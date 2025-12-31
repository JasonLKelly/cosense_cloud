"""FastAPI application for the API Gateway."""

import asyncio
import json
import logging
import time
import uuid
from collections import deque
from contextlib import asynccontextmanager
from typing import Literal

import httpx
from confluent_kafka import Consumer, KafkaError
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from .config import settings
from .gemini import ask_copilot, ask_copilot_stream, OperatorAnswer
from .activity import activity_buffer, emit_decision, emit_anomaly

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# In-memory state buffers
class StateBuffer:
    """Buffers for recent state and decisions."""

    def __init__(self):
        self.decisions: deque[dict] = deque(maxlen=settings.max_decisions_buffer)
        self.robot_states: dict[str, deque[dict]] = {}
        self.current_state: dict[str, dict] = {}  # Latest state per robot
        self.anomaly_alerts: deque[dict] = deque(maxlen=settings.max_anomalies_buffer)
        self.dismissed_alert_ids: set[str] = set()
        self.shift_summaries: deque[dict] = deque(maxlen=settings.max_summaries_buffer)

    def add_decision(self, decision: dict):
        self.decisions.append(decision)

    def add_robot_state(self, state: dict):
        robot_id = state["robot_id"]
        if robot_id not in self.robot_states:
            self.robot_states[robot_id] = deque(maxlen=settings.max_state_buffer)
        self.robot_states[robot_id].append(state)
        self.current_state[robot_id] = state

    def add_anomaly_alert(self, alert: dict):
        # Skip if already dismissed
        if alert.get("alert_id") in self.dismissed_alert_ids:
            return
        self.anomaly_alerts.append(alert)

    def dismiss_anomaly(self, alert_id: str) -> bool:
        """Dismiss an anomaly alert. Returns True if found and dismissed."""
        self.dismissed_alert_ids.add(alert_id)
        # Remove from current buffer
        for i, alert in enumerate(self.anomaly_alerts):
            if alert.get("alert_id") == alert_id:
                del self.anomaly_alerts[i]
                return True
        return False

    def get_active_anomalies(self) -> list[dict]:
        """Get anomalies that haven't been dismissed."""
        return [a for a in self.anomaly_alerts if a.get("alert_id") not in self.dismissed_alert_ids]

    def clear_all_anomalies(self):
        """Clear all anomaly alerts."""
        # Mark all current alerts as dismissed
        for alert in self.anomaly_alerts:
            if alert.get("alert_id"):
                self.dismissed_alert_ids.add(alert.get("alert_id"))
        self.anomaly_alerts.clear()

    def add_shift_summary(self, summary: dict):
        """Add a shift summary from Flink."""
        self.shift_summaries.append(summary)


buffer = StateBuffer()
consumer: Consumer | None = None
consumer_task: asyncio.Task | None = None

# Simple cache for simulator state to reduce proxy latency
class SimulatorStateCache:
    """Cache simulator state to avoid repeated HTTP calls."""
    def __init__(self, ttl_ms: int = 100):
        self.ttl_ms = ttl_ms
        self.cached_state: dict | None = None
        self.cached_at: float = 0
        self._lock = asyncio.Lock()

    async def get_state(self, simulator_url: str) -> dict:
        """Get state from cache or fetch from simulator."""
        now = time.time() * 1000
        if self.cached_state and (now - self.cached_at) < self.ttl_ms:
            return self.cached_state

        async with self._lock:
            # Double-check after acquiring lock
            now = time.time() * 1000
            if self.cached_state and (now - self.cached_at) < self.ttl_ms:
                return self.cached_state

            async with httpx.AsyncClient() as client:
                response = await client.get(f"{simulator_url}/state")
                self.cached_state = response.json()
                self.cached_at = time.time() * 1000
                return self.cached_state

sim_state_cache = SimulatorStateCache(ttl_ms=100)


def create_consumer() -> Consumer:
    """Create Kafka consumer."""
    config = settings.get_kafka_config()
    config["group.id"] = settings.prefixed_consumer_group
    config["auto.offset.reset"] = "earliest"
    return Consumer(config)


async def consume_loop():
    """Background task to consume Kafka messages with retry."""
    global consumer

    while True:
        try:
            consumer = create_consumer()
            topics = [
                settings.topic(settings.coordination_decisions_topic),
                settings.topic(settings.coordination_state_topic),
                settings.topic(settings.anomaly_alerts_topic),
                settings.topic(settings.shift_summaries_topic),
            ]
            consumer.subscribe(topics)
            logger.info(f"Kafka consumer subscribed to: {topics}")

            while True:
                msg = consumer.poll(timeout=0.1)
                if msg is None:
                    await asyncio.sleep(0.01)
                    continue

                if msg.error():
                    if msg.error().code() != KafkaError._PARTITION_EOF:
                        logger.error(f"Kafka error: {msg.error()}")
                    continue

                try:
                    topic = msg.topic()
                    raw = msg.value()
                    # Strip 5-byte Schema Registry header if present (magic byte + schema ID)
                    if raw[:1] == b'\x00':
                        raw = raw[5:]
                    value = json.loads(raw.decode("utf-8"))

                    if topic == settings.topic(settings.coordination_decisions_topic):
                        buffer.add_decision(value)
                        # Emit activity event
                        await emit_decision(
                            robot_id=value.get("robot_id", ""),
                            action=value.get("action", ""),
                            reason_codes=value.get("reason_codes", []),
                            risk_score=value.get("risk_score", 0),
                        )
                    elif topic == settings.topic(settings.coordination_state_topic):
                        buffer.add_robot_state(value)
                    elif topic == settings.topic(settings.anomaly_alerts_topic):
                        buffer.add_anomaly_alert(value)
                        await emit_anomaly(
                            alert_type=value.get("alert_type", ""),
                            severity=value.get("severity", ""),
                            robot_id=value.get("robot_id"),
                            actual_value=value.get("actual_value", 0),
                            forecast_value=value.get("forecast_value", 1),
                        )
                    elif topic == settings.topic(settings.shift_summaries_topic):
                        buffer.add_shift_summary(value)
                        logger.info(f"Received shift summary: {value.get('summary_id')}")

                except Exception as e:
                    logger.error(f"Error processing message: {e}")

                await asyncio.sleep(0)  # Yield to event loop

        except Exception as e:
            logger.warning(f"Kafka consumer error, retrying in 2s: {e}")
            if consumer:
                try:
                    consumer.close()
                except Exception:
                    pass
                consumer = None
            await asyncio.sleep(2)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan."""
    global consumer_task

    # Start Kafka consumer
    consumer_task = asyncio.create_task(consume_loop())
    logger.info("Backend started")

    yield

    # Cleanup
    if consumer_task:
        consumer_task.cancel()
        try:
            await consumer_task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title="CoSense Backend",
    description="Backend for CoSense Cloud - connects UI to streaming data and Gemini copilot",
    version="0.1.0",
    lifespan=lifespan,
)

# GZip compression for responses > 500 bytes
app.add_middleware(GZipMiddleware, minimum_size=500)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response models
class ChatMessage(BaseModel):
    role: str  # "user" or "model"
    content: str


class QuestionRequest(BaseModel):
    question: str
    history: list[ChatMessage] = []


class ScenarioToggle(BaseModel):
    visibility: Literal["normal", "degraded", "poor"] | None = None
    connectivity: Literal["normal", "degraded", "offline"] | None = None


class ScaleRequest(BaseModel):
    robots: int | None = None
    humans: int | None = None


# Health check
@app.get("/health")
async def health():
    return {"status": "healthy"}


# State endpoints
@app.get("/state")
async def get_state():
    """Get current coordination state for all robots."""
    return {
        "robots": buffer.current_state,
    }


@app.get("/decisions")
async def get_decisions(limit: int = 20):
    """Get recent coordination decisions."""
    return list(buffer.decisions)[-limit:]


@app.get("/decisions/{robot_id}")
async def get_robot_decisions(robot_id: str, limit: int = 10):
    """Get recent decisions for a specific robot."""
    robot_decisions = [d for d in buffer.decisions if d["robot_id"] == robot_id]
    return robot_decisions[-limit:]


# Anomaly alerts endpoints
@app.get("/anomalies")
async def get_anomalies(limit: int = 20):
    """Get recent anomaly alerts from Flink AI pipeline."""
    return buffer.get_active_anomalies()[-limit:]


@app.get("/anomalies/{robot_id}")
async def get_robot_anomalies(robot_id: str, limit: int = 10):
    """Get recent anomaly alerts for a specific robot."""
    robot_anomalies = [a for a in buffer.get_active_anomalies() if a.get("robot_id") == robot_id]
    return robot_anomalies[-limit:]


@app.delete("/anomalies")
async def clear_all_anomalies():
    """Clear all anomaly alerts."""
    buffer.clear_all_anomalies()
    return {"status": "cleared"}


@app.delete("/anomalies/{alert_id}")
async def dismiss_anomaly(alert_id: str):
    """Dismiss an anomaly alert (removes it from the list)."""
    buffer.dismiss_anomaly(alert_id)
    return {"status": "dismissed", "alert_id": alert_id}


# Shift summary endpoints
@app.get("/summary/latest")
async def get_latest_summary():
    """Get the most recent shift summary from Flink.

    Returns the latest AI-generated performance report with AutoML classification
    and Gemini-generated narrative. Returns null if no summaries available.
    """
    if not buffer.shift_summaries:
        return None
    return buffer.shift_summaries[-1]


@app.get("/summary/history")
async def get_summary_history(limit: int = 10):
    """Get recent shift summaries."""
    return list(buffer.shift_summaries)[-limit:]


@app.post("/summary/generate")
async def generate_summary_on_demand():
    """Generate a summary on-demand (for demo purposes).

    This bypasses Flink and calls Gemini directly with the current buffered data.
    Use this when you can't wait for the next 5-minute Flink window.
    """
    from .gemini import generate_performance_summary

    summary = await generate_performance_summary(
        decisions=list(buffer.decisions),
        anomaly_alerts=list(buffer.anomaly_alerts),
    )
    return summary


# SSE stream for real-time updates
@app.get("/stream")
async def stream_updates():
    """Server-Sent Events stream for real-time state updates."""

    async def event_generator():
        last_decision_count = len(buffer.decisions)
        last_states = dict(buffer.current_state)

        while True:
            # Check for new decisions
            if len(buffer.decisions) > last_decision_count:
                new_decisions = list(buffer.decisions)[last_decision_count:]
                for dec in new_decisions:
                    yield {
                        "event": "decision",
                        "data": json.dumps(dec),
                    }
                last_decision_count = len(buffer.decisions)

            # Check for state changes
            for robot_id, state in buffer.current_state.items():
                if robot_id not in last_states or state != last_states[robot_id]:
                    yield {
                        "event": "state",
                        "data": json.dumps(state),
                    }
                    last_states[robot_id] = state

            await asyncio.sleep(0.1)

    return EventSourceResponse(event_generator())


# SSE stream for pipeline activity (for Pipeline Activity page)
@app.get("/stream/activity")
async def stream_activity():
    """Server-Sent Events stream for pipeline activity events.

    Events include:
    - tool_call: Gemini tool invocations
    - decision: Coordination decisions from stream processor
    - anomaly: AI-detected anomalies from Flink pipeline
    """

    async def event_generator():
        # Subscribe to activity buffer
        queue = await activity_buffer.subscribe()

        try:
            # Send recent events first
            for event in activity_buffer.get_recent(30):
                yield {
                    "event": "activity",
                    "data": json.dumps(event.model_dump()),
                }

            # Stream new events
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield {
                        "event": "activity",
                        "data": json.dumps(event.model_dump()),
                    }
                except asyncio.TimeoutError:
                    # Send keepalive
                    yield {"event": "keepalive", "data": "{}"}
        finally:
            await activity_buffer.unsubscribe(queue)

    return EventSourceResponse(event_generator())


# Operator Q&A
@app.post("/ask", response_model=OperatorAnswer)
async def ask_question(request: QuestionRequest):
    """Ask a question to the Gemini operator copilot.

    Gemini has access to tools that query robot state, decisions,
    zone context, and patterns. It decides which tools to call
    based on the question.
    """
    # Convert deques to lists for tool context
    robot_states = {
        robot_id: list(states)
        for robot_id, states in buffer.robot_states.items()
    }

    # Convert history to list of dicts
    history = [{"role": m.role, "content": m.content} for m in request.history]

    answer = await ask_copilot(
        question=request.question,
        history=history,
        decisions=list(buffer.decisions),
        robot_states=robot_states,
        current_state=buffer.current_state,
        anomaly_alerts=list(buffer.anomaly_alerts),
    )

    return answer


@app.post("/ask/stream")
async def ask_question_stream(request: QuestionRequest):
    """Stream a response from the Gemini operator copilot.

    Returns Server-Sent Events with JSON payloads:
    - {"type": "tool", "name": "..."} - tool being called
    - {"type": "chunk", "text": "..."} - text chunk
    - {"type": "done", "confidence": "HIGH"} - completion
    - {"type": "error", "message": "..."} - error
    """
    robot_states = {
        robot_id: list(states)
        for robot_id, states in buffer.robot_states.items()
    }
    history = [{"role": m.role, "content": m.content} for m in request.history]

    async def event_generator():
        async for event in ask_copilot_stream(
            question=request.question,
            history=history,
            decisions=list(buffer.decisions),
            robot_states=robot_states,
            current_state=buffer.current_state,
            anomaly_alerts=list(buffer.anomaly_alerts),
        ):
            yield {"data": event}

    return EventSourceResponse(event_generator())


# Proxy endpoints to simulator
@app.post("/scenario/start")
async def start_scenario():
    """Start the simulation (proxied to simulator)."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(f"{settings.simulator_url}/scenario/start")
            return response.json()
        except httpx.RequestError as e:
            raise HTTPException(status_code=503, detail=f"Simulator unavailable: {e}")


@app.post("/scenario/stop")
async def stop_scenario():
    """Stop the simulation (proxied to simulator)."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(f"{settings.simulator_url}/scenario/stop")
            return response.json()
        except httpx.RequestError as e:
            raise HTTPException(status_code=503, detail=f"Simulator unavailable: {e}")


@app.post("/scenario/toggle")
async def toggle_scenario(toggle: ScenarioToggle):
    """Toggle scenario conditions (proxied to simulator)."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{settings.simulator_url}/scenario/toggle",
                json=toggle.model_dump(exclude_none=True),
            )
            return response.json()
        except httpx.RequestError as e:
            raise HTTPException(status_code=503, detail=f"Simulator unavailable: {e}")


@app.post("/scenario/scale")
async def scale_scenario(scale: ScaleRequest):
    """Scale the simulation (proxied to simulator)."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{settings.simulator_url}/scenario/scale",
                json=scale.model_dump(exclude_none=True),
            )
            return response.json()
        except httpx.RequestError as e:
            raise HTTPException(status_code=503, detail=f"Simulator unavailable: {e}")


class ResetRequest(BaseModel):
    """Parameters for resetting the simulation."""
    robots: int | None = None
    humans: int | None = None
    visibility: str | None = None
    connectivity: str | None = None


@app.post("/scenario/reset")
async def reset_scenario(params: ResetRequest | None = None):
    """Reset the simulation (proxied to simulator)."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{settings.simulator_url}/scenario/reset",
                json=params.model_dump(exclude_none=True) if params else None,
            )
            return response.json()
        except httpx.RequestError as e:
            raise HTTPException(status_code=503, detail=f"Simulator unavailable: {e}")


# Get simulator state (cached to reduce latency)
@app.get("/simulator/state")
async def get_simulator_state():
    """Get current simulator state (for UI rendering)."""
    try:
        return await sim_state_cache.get_state(settings.simulator_url)
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Simulator unavailable: {e}")


# Robot control endpoints (proxied to simulator)
@app.post("/robots/{robot_id}/stop")
async def stop_robot(robot_id: str):
    """Stop a specific robot."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(f"{settings.simulator_url}/robots/{robot_id}/stop")
            return response.json()
        except httpx.RequestError as e:
            raise HTTPException(status_code=503, detail=f"Simulator unavailable: {e}")


@app.post("/robots/{robot_id}/start")
async def start_robot(robot_id: str):
    """Start a specific robot."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(f"{settings.simulator_url}/robots/{robot_id}/start")
            return response.json()
        except httpx.RequestError as e:
            raise HTTPException(status_code=503, detail=f"Simulator unavailable: {e}")


# Debug endpoints
class MockAnomalyRequest(BaseModel):
    """Request for generating a mock anomaly alert."""
    alert_type: Literal[
        "DECISION_RATE_SPIKE",
        "REPEATED_ROBOT_STOP",
        "SENSOR_DISAGREEMENT_SPIKE"
    ] = "DECISION_RATE_SPIKE"
    severity: Literal["HIGH", "MEDIUM"] = "HIGH"
    robot_id: str | None = None


@app.post("/debug/mock-anomaly")
async def create_mock_anomaly(request: MockAnomalyRequest | None = None):
    """Create a mock anomaly alert for UI testing.

    This endpoint allows testing the AI Alerts panel before Flink is deployed.
    """
    req = request or MockAnomalyRequest()
    now_ms = int(time.time() * 1000)

    # Generate context based on alert type
    contexts = {
        "DECISION_RATE_SPIKE": {
            "context": "Decision rate exceeded normal bounds - 15 decisions in last 30s vs expected 5",
            "metric_name": "decision_count",
            "actual_value": 15.0,
            "forecast_value": 5.2,
        },
        "REPEATED_ROBOT_STOP": {
            "context": f"Robot {req.robot_id or 'robot-1'} stopped 3 times in last 30s",
            "metric_name": "stop_count_30s",
            "actual_value": 3.0,
            "forecast_value": 0.5,
        },
        "SENSOR_DISAGREEMENT_SPIKE": {
            "context": "4 sensor disagreements detected in last 30s vs expected <1",
            "metric_name": "sensor_disagreement_count",
            "actual_value": 4.0,
            "forecast_value": 0.8,
        },
    }

    alert_data = contexts[req.alert_type]
    alert = {
        "alert_id": f"{req.alert_type.lower()[:3]}-{now_ms}",
        "alert_type": req.alert_type,
        "detected_at": now_ms,
        "robot_id": req.robot_id or ("robot-1" if req.alert_type == "REPEATED_ROBOT_STOP" else None),
        "metric_name": alert_data["metric_name"],
        "actual_value": alert_data["actual_value"],
        "forecast_value": alert_data["forecast_value"],
        "lower_bound": alert_data["forecast_value"] * 0.5,
        "upper_bound": alert_data["forecast_value"] * 1.5,
        "severity": req.severity,
        "context": alert_data["context"],
    }

    buffer.add_anomaly_alert(alert)
    return {"status": "created", "alert": alert}


# Map endpoint
@app.get("/map/{map_id}")
async def get_map(map_id: str):
    """Get warehouse map definition.

    The map is loaded from the maps/ directory and includes:
    - Zone definitions
    - Obstacles (racks, conveyors, workstations)
    - Named waypoints for navigation
    """
    from pathlib import Path

    # Look for map file - try multiple locations
    possible_paths = [
        Path("/app/maps") / f"{map_id}.json",  # Docker mount
        Path(__file__).parent.parent.parent.parent / "maps" / f"{map_id}.json",  # Local dev
        Path(__file__).parent.parent / "maps" / f"{map_id}.json",  # Alternative
    ]

    map_file = None
    for path in possible_paths:
        if path.exists():
            map_file = path
            break

    if not map_file:
        raise HTTPException(status_code=404, detail=f"Map '{map_id}' not found")

    try:
        with open(map_file) as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"Invalid map file: {e}")
