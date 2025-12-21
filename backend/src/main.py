"""FastAPI application for the API Gateway."""

import asyncio
import json
import logging
from collections import deque
from contextlib import asynccontextmanager
from typing import Literal

import httpx
from confluent_kafka import Consumer, KafkaError
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from .config import settings
from .gemini import ask_copilot, OperatorAnswer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# In-memory state buffers
class StateBuffer:
    """Buffers for recent state and decisions."""

    def __init__(self):
        self.decisions: deque[dict] = deque(maxlen=settings.max_decisions_buffer)
        self.robot_states: dict[str, deque[dict]] = {}
        self.zone_states: dict[str, dict] = {}
        self.current_state: dict[str, dict] = {}  # Latest state per robot

    def add_decision(self, decision: dict):
        self.decisions.append(decision)

    def add_robot_state(self, state: dict):
        robot_id = state["robot_id"]
        if robot_id not in self.robot_states:
            self.robot_states[robot_id] = deque(maxlen=settings.max_state_buffer)
        self.robot_states[robot_id].append(state)
        self.current_state[robot_id] = state

    def update_zone(self, zone: dict):
        self.zone_states[zone["zone_id"]] = zone


buffer = StateBuffer()
consumer: Consumer | None = None
consumer_task: asyncio.Task | None = None


def create_consumer() -> Consumer:
    """Create Kafka consumer."""
    config = settings.get_kafka_config()
    config["group.id"] = settings.consumer_group
    config["auto.offset.reset"] = "latest"
    return Consumer(config)


async def consume_loop():
    """Background task to consume Kafka messages."""
    global consumer

    try:
        consumer = create_consumer()
        consumer.subscribe([
            settings.coordination_decisions_topic,
            settings.coordination_state_topic,
        ])
        logger.info("Kafka consumer started")

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
                value = json.loads(msg.value().decode("utf-8"))

                if topic == settings.coordination_decisions_topic:
                    buffer.add_decision(value)
                elif topic == settings.coordination_state_topic:
                    buffer.add_robot_state(value)

            except Exception as e:
                logger.error(f"Error processing message: {e}")

            await asyncio.sleep(0)  # Yield to event loop

    except Exception as e:
        logger.error(f"Consumer error: {e}")
    finally:
        if consumer:
            consumer.close()


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

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response models
class QuestionRequest(BaseModel):
    question: str


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
        "zones": buffer.zone_states,
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

    answer = await ask_copilot(
        question=request.question,
        decisions=list(buffer.decisions),
        robot_states=robot_states,
        zone_states=buffer.zone_states,
        current_state=buffer.current_state,
    )

    return answer


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


@app.post("/scenario/reset")
async def reset_scenario():
    """Reset the simulation (proxied to simulator)."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(f"{settings.simulator_url}/scenario/reset")
            return response.json()
        except httpx.RequestError as e:
            raise HTTPException(status_code=503, detail=f"Simulator unavailable: {e}")


# Get simulator state directly
@app.get("/simulator/state")
async def get_simulator_state():
    """Get current simulator state (for UI rendering)."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{settings.simulator_url}/state")
            return response.json()
        except httpx.RequestError as e:
            raise HTTPException(status_code=503, detail=f"Simulator unavailable: {e}")
