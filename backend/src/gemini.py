"""Gemini copilot with tool calling for operator Q&A."""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from typing import Any, AsyncIterator

import httpx
from google import genai
from google.genai import types
from pydantic import BaseModel

from .config import settings

logger = logging.getLogger(__name__)


# ============================================================================
# Response Schema
# ============================================================================

class EvidenceItem(BaseModel):
    """A piece of evidence supporting the answer."""
    signal: str
    value: str
    relevance: str


class ToolCallLog(BaseModel):
    """Record of a tool call made during answering."""
    tool: str
    params: dict
    success: bool


class OperatorAnswer(BaseModel):
    """Structured answer to an operator question."""
    summary: str
    confidence: str  # HIGH, MEDIUM, LOW, INSUFFICIENT
    evidence: list[EvidenceItem] = []
    is_pattern: bool | None = None
    pattern_description: str | None = None
    tool_calls: list[ToolCallLog] = []
    error: str | None = None


# ============================================================================
# Tool Context - shared state accessible by tool functions
# ============================================================================

@dataclass
class ToolContext:
    """Context available to tool functions during a question."""
    decisions: list[dict] = field(default_factory=list)
    robot_states: dict[str, list[dict]] = field(default_factory=dict)
    zone_states: dict[str, dict] = field(default_factory=dict)
    current_state: dict[str, dict] = field(default_factory=dict)
    anomaly_alerts: list[dict] = field(default_factory=list)
    simulator_url: str = "http://simulator:8000"


# Module-level context, set before each Gemini call
_ctx: ToolContext = ToolContext()


def set_tool_context(ctx: ToolContext) -> None:
    """Set the context for tool functions."""
    global _ctx
    _ctx = ctx


# ============================================================================
# Tool Functions - these are called automatically by the SDK
# ============================================================================

def get_robot_state(robot_id: str, window_sec: int = 30) -> dict:
    """Get a robot's current state and recent trajectory.

    Args:
        robot_id: The robot identifier (e.g., "robot-1")
        window_sec: How far back to look in seconds (default 30)

    Returns:
        Current position, velocity, sensors, and recent trajectory points
    """
    import httpx

    # Get current state from Kafka buffer
    current = _ctx.current_state.get(robot_id)

    # Fallback: fetch from simulator if not in Kafka buffer
    if not current:
        try:
            with httpx.Client(timeout=2.0) as client:
                resp = client.get(f"{_ctx.simulator_url}/state")
                sim_state = resp.json()
                for robot in sim_state.get("robots", []):
                    if robot.get("robot_id") == robot_id:
                        return {
                            "robot_id": robot_id,
                            "current": {
                                "x": robot.get("x"),
                                "y": robot.get("y"),
                                "velocity": robot.get("velocity"),
                                "heading": robot.get("heading"),
                                "motion_state": robot.get("motion_state"),
                                "commanded_action": robot.get("commanded_action"),
                            },
                            "sensors": {},
                            "trajectory": [],
                            "source": "simulator",
                        }
        except Exception:
            pass
        return {"error": f"Robot {robot_id} not found", "robot_id": robot_id}

    # Get historical states
    history = _ctx.robot_states.get(robot_id, [])
    trajectory = [
        {"x": s.get("x"), "y": s.get("y"), "velocity": s.get("velocity")}
        for s in history[-10:]  # Last 10 points
    ]

    return {
        "robot_id": robot_id,
        "current": {
            "x": current.get("x"),
            "y": current.get("y"),
            "velocity": current.get("velocity"),
            "heading": current.get("heading"),
            "status": current.get("status"),
            "risk_score": current.get("risk_score"),
        },
        "sensors": {
            "ultrasonic_cm": current.get("ultrasonic_cm"),
            "ble_nearest_human": current.get("ble_nearest_human"),
            "ble_distance_m": current.get("ble_distance_m"),
        },
        "trajectory": trajectory,
        "source": "kafka",
    }


def get_nearby_entities(robot_id: str, radius_m: float = 5.0) -> dict:
    """Get humans and other robots near a specific robot.

    Args:
        robot_id: The robot to check proximity for
        radius_m: Search radius in meters (default 5.0)

    Returns:
        List of nearby humans and robots with distances
    """
    robot_state = _ctx.current_state.get(robot_id)
    if not robot_state:
        return {"error": f"Robot {robot_id} not found", "robot_id": robot_id}

    # Get proximity info from robot state (computed by stream processor)
    nearby_humans = []
    if robot_state.get("nearest_human_id"):
        nearby_humans.append({
            "human_id": robot_state.get("nearest_human_id"),
            "distance_m": robot_state.get("nearest_human_distance"),
        })

    # Check other robots
    nearby_robots = []
    rx, ry = robot_state.get("x", 0), robot_state.get("y", 0)
    for rid, state in _ctx.current_state.items():
        if rid == robot_id or not rid.startswith("robot"):
            continue
        ox, oy = state.get("x", 0), state.get("y", 0)
        dist = ((rx - ox) ** 2 + (ry - oy) ** 2) ** 0.5
        if dist <= radius_m:
            nearby_robots.append({
                "robot_id": rid,
                "distance_m": round(dist, 2),
                "velocity": state.get("velocity"),
            })

    return {
        "robot_id": robot_id,
        "position": {"x": rx, "y": ry},
        "nearby_humans": nearby_humans,
        "nearby_robots": nearby_robots,
    }


def get_decisions(
    robot_id: str | None = None,
    zone_id: str | None = None,
    action: str | None = None,
    limit: int = 10
) -> dict:
    """Get recent coordination decisions with optional filters.

    Args:
        robot_id: Filter by robot (optional)
        zone_id: Filter by zone (optional)
        action: Filter by action type: STOP, SLOW, REROUTE, CONTINUE (optional)
        limit: Maximum number of decisions to return (default 10)

    Returns:
        List of recent decisions with reasons and timestamps
    """
    decisions = _ctx.decisions

    # Apply filters
    if robot_id:
        decisions = [d for d in decisions if d.get("robot_id") == robot_id]
    if zone_id:
        decisions = [d for d in decisions if d.get("zone_id") == zone_id]
    if action:
        decisions = [d for d in decisions if d.get("action") == action]

    # Take most recent
    recent = decisions[-limit:] if len(decisions) > limit else decisions

    return {
        "count": len(recent),
        "filters": {"robot_id": robot_id, "zone_id": zone_id, "action": action},
        "decisions": [
            {
                "robot_id": d.get("robot_id"),
                "action": d.get("action"),
                "reason_codes": d.get("reason_codes", []),
                "risk_score": d.get("risk_score"),
                "summary": d.get("summary"),
                "timestamp": d.get("timestamp"),
            }
            for d in recent
        ],
    }


def get_zone_context(zone_id: str) -> dict:
    """Get current zone environmental status.

    Args:
        zone_id: The zone identifier (e.g., "zone-c")

    Returns:
        Zone visibility, congestion level, entity counts, connectivity status
    """
    zone = _ctx.zone_states.get(zone_id)
    if not zone:
        return {"error": f"Zone {zone_id} not found", "zone_id": zone_id}

    return {
        "zone_id": zone_id,
        "visibility": zone.get("visibility", "unknown"),
        "congestion_level": zone.get("congestion_level", 0),
        "connectivity": zone.get("connectivity", "unknown"),
        "robot_count": zone.get("robot_count", 0),
        "human_count": zone.get("human_count", 0),
    }


def get_anomalies(
    robot_id: str | None = None,
    severity: str | None = None,
    alert_type: str | None = None,
    limit: int = 10
) -> dict:
    """Get recent anomaly alerts detected by the Flink AI pipeline.

    Anomalies are detected using ML_DETECT_ANOMALIES (ARIMA) and enriched
    with AI explanations via ML_PREDICT (Gemini).

    Args:
        robot_id: Filter by robot (optional)
        severity: Filter by severity: HIGH, MEDIUM (optional)
        alert_type: Filter by type: DECISION_RATE_SPIKE, REPEATED_ROBOT_STOP, SENSOR_DISAGREEMENT_SPIKE (optional)
        limit: Maximum number of alerts to return (default 10)

    Returns:
        List of recent anomaly alerts with AI explanations
    """
    anomalies = _ctx.anomaly_alerts

    # Apply filters
    if robot_id:
        anomalies = [a for a in anomalies if a.get("robot_id") == robot_id]
    if severity:
        anomalies = [a for a in anomalies if a.get("severity") == severity]
    if alert_type:
        anomalies = [a for a in anomalies if a.get("alert_type") == alert_type]

    # Take most recent
    recent = anomalies[-limit:] if len(anomalies) > limit else anomalies

    return {
        "count": len(recent),
        "filters": {"robot_id": robot_id, "severity": severity, "alert_type": alert_type},
        "anomalies": [
            {
                "alert_id": a.get("alert_id"),
                "alert_type": a.get("alert_type"),
                "severity": a.get("severity"),
                "robot_id": a.get("robot_id"),
                "zone_id": a.get("zone_id"),
                "context": a.get("context"),
                "ai_explanation": a.get("ai_explanation"),
                "detected_at": a.get("detected_at"),
            }
            for a in recent
        ],
    }


def get_scenario_status() -> dict:
    """Get current simulation state and configuration.

    Returns:
        Whether simulation is running, entity counts, scenario toggles
    """
    try:
        with httpx.Client(timeout=2.0) as client:
            response = client.get(f"{_ctx.simulator_url}/scenario/status")
            if response.status_code == 200:
                return response.json()
            return {"error": f"Simulator returned {response.status_code}"}
    except Exception as e:
        return {"error": f"Could not reach simulator: {str(e)}"}


def start_simulation() -> dict:
    """Start the robot simulation.

    Call this when the operator asks to start, run, or begin the simulation.

    Returns:
        Confirmation that simulation started, or error message
    """
    try:
        with httpx.Client(timeout=2.0) as client:
            response = client.post(f"{_ctx.simulator_url}/scenario/start")
            if response.status_code == 200:
                return response.json()
            return {"error": f"Simulator returned {response.status_code}"}
    except Exception as e:
        return {"error": f"Could not reach simulator: {str(e)}"}


def stop_simulation() -> dict:
    """Stop the robot simulation.

    Call this when the operator asks to stop, pause, or halt the simulation.

    Returns:
        Confirmation that simulation stopped, or error message
    """
    try:
        with httpx.Client(timeout=2.0) as client:
            response = client.post(f"{_ctx.simulator_url}/scenario/stop")
            if response.status_code == 200:
                return response.json()
            return {"error": f"Simulator returned {response.status_code}"}
    except Exception as e:
        return {"error": f"Could not reach simulator: {str(e)}"}


def reset_simulation() -> dict:
    """Reset the robot simulation to initial state.

    Call this when the operator asks to reset, restart, or reinitialize.
    This stops the simulation and clears all state.

    Returns:
        Confirmation that simulation was reset, or error message
    """
    try:
        with httpx.Client(timeout=2.0) as client:
            response = client.post(f"{_ctx.simulator_url}/scenario/reset")
            if response.status_code == 200:
                return response.json()
            return {"error": f"Simulator returned {response.status_code}"}
    except Exception as e:
        return {"error": f"Could not reach simulator: {str(e)}"}


def stop_robot(robot_id: str) -> dict:
    """Stop a specific robot.

    Call this when the operator asks to stop a particular robot.
    Example: "Stop robot-1" or "Halt robot 2"

    Args:
        robot_id: The robot identifier (e.g., "robot-1", "robot-2")

    Returns:
        Confirmation that robot was stopped, or error message
    """
    try:
        with httpx.Client(timeout=2.0) as client:
            response = client.post(f"{_ctx.simulator_url}/robots/{robot_id}/stop")
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                return {"error": f"Robot {robot_id} not found"}
            return {"error": f"Simulator returned {response.status_code}"}
    except Exception as e:
        return {"error": f"Could not reach simulator: {str(e)}"}


def start_robot(robot_id: str) -> dict:
    """Start/resume a specific robot.

    Call this when the operator asks to start, resume, or continue a particular robot.
    Example: "Start robot-1" or "Resume robot 2"

    Args:
        robot_id: The robot identifier (e.g., "robot-1", "robot-2")

    Returns:
        Confirmation that robot was started, or error message
    """
    try:
        with httpx.Client(timeout=2.0) as client:
            response = client.post(f"{_ctx.simulator_url}/robots/{robot_id}/start")
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                return {"error": f"Robot {robot_id} not found"}
            return {"error": f"Simulator returned {response.status_code}"}
    except Exception as e:
        return {"error": f"Could not reach simulator: {str(e)}"}


def analyze_patterns(window_sec: int = 300, group_by: str = "action") -> dict:
    """Analyze patterns in recent decisions for trend detection.

    Args:
        window_sec: Time window to analyze in seconds (default 300 = 5 min)
        group_by: How to group results: "action", "reason_code", "robot_id", "zone_id"

    Returns:
        Aggregated counts and distribution of decisions
    """
    decisions = _ctx.decisions

    # Group and count
    counts: dict[str, int] = {}
    for d in decisions:
        if group_by == "action":
            key = d.get("action", "unknown")
            counts[key] = counts.get(key, 0) + 1
        elif group_by == "reason_code":
            for reason in d.get("reason_codes", []):
                counts[reason] = counts.get(reason, 0) + 1
        elif group_by == "robot_id":
            key = d.get("robot_id", "unknown")
            counts[key] = counts.get(key, 0) + 1
        elif group_by == "zone_id":
            key = d.get("zone_id", "unknown")
            counts[key] = counts.get(key, 0) + 1

    # Calculate total and percentages
    total = sum(counts.values())
    distribution = {
        k: {"count": v, "percent": round(100 * v / total, 1) if total > 0 else 0}
        for k, v in counts.items()
    }

    return {
        "window_sec": window_sec,
        "group_by": group_by,
        "total_decisions": len(decisions),
        "distribution": distribution,
    }


# All available tools
TOOLS = [
    # Query tools
    get_robot_state,
    get_nearby_entities,
    get_decisions,
    get_anomalies,
    get_zone_context,
    get_scenario_status,
    analyze_patterns,
    # Simulation control tools
    start_simulation,
    stop_simulation,
    reset_simulation,
    # Individual robot control tools
    stop_robot,
    start_robot,
]


# ============================================================================
# System Prompt
# ============================================================================

SYSTEM_PROMPT = """You are an operator copilot for CoSense, a warehouse robot coordination system.

Your job is to help operators understand and control what's happening with robots, humans, and zones.

QUERY TOOLS:
- get_robot_state: Get a robot's position, velocity, sensors, and trajectory
- get_nearby_entities: Find humans and robots near a specific robot
- get_decisions: Get recent coordination decisions (STOP, SLOW, REROUTE, CONTINUE)
- get_anomalies: Get AI-detected anomalies from Flink pipeline (spikes, patterns)
- get_zone_context: Get zone conditions (visibility, congestion, connectivity)
- get_scenario_status: Get simulation status (running, entity counts, toggles)
- analyze_patterns: Analyze decision patterns and trends

SIMULATION CONTROL TOOLS:
- start_simulation: Start the robot simulation
- stop_simulation: Stop/pause the simulation
- reset_simulation: Reset simulation to initial state

ROBOT CONTROL TOOLS:
- stop_robot(robot_id): Stop a specific robot (e.g., "stop robot-1")
- start_robot(robot_id): Resume a specific robot (e.g., "start robot-1")

ANOMALY TYPES:
- DECISION_RATE_SPIKE: Unusual increase in safety decisions (detected by ARIMA)
- REPEATED_ROBOT_STOP: Same robot stopped multiple times in 30s
- SENSOR_DISAGREEMENT_SPIKE: Ultrasonic/BLE sensors conflicting

RULES:
1. Use query tools to gather data before answering questions
2. Use control tools when the operator asks to start, stop, or reset
3. For individual robot commands, use stop_robot/start_robot with the robot_id
4. ONLY state facts that come from tool results - never invent data
5. Cite specific values (distances, speeds, scores) as evidence
6. If data is insufficient, say so clearly
7. Be concise but complete
8. When asked about anomalies or alerts, use get_anomalies

When answering questions:
- Explain WHY things happened by citing reason_codes and sensor data
- For patterns, use analyze_patterns and look at distributions
- For anomalies, include the AI explanation from the alert
- Always ground your answer in the data you retrieved"""


# ============================================================================
# Gemini Client
# ============================================================================

_client: genai.Client | None = None


def get_client() -> genai.Client | None:
    """Get or create the Gemini client."""
    global _client

    if _client is not None:
        return _client

    try:
        if settings.use_vertex_ai:
            if not settings.google_cloud_project:
                logger.warning("GOOGLE_CLOUD_PROJECT not set - Gemini disabled")
                return None
            _client = genai.Client(
                vertexai=True,
                project=settings.google_cloud_project,
                location=settings.google_cloud_location,
            )
            logger.info(f"Gemini client initialized (Vertex AI: {settings.google_cloud_project})")
        else:
            if not settings.google_api_key:
                logger.warning("GOOGLE_API_KEY not set - Gemini disabled")
                return None
            _client = genai.Client(api_key=settings.google_api_key)
            logger.info("Gemini client initialized (API key)")

        return _client
    except Exception as e:
        logger.error(f"Failed to initialize Gemini client: {e}")
        return None


# ============================================================================
# Main Entry Point
# ============================================================================

async def ask_copilot(
    question: str,
    history: list[dict],
    decisions: list[dict],
    robot_states: dict[str, list[dict]],
    zone_states: dict[str, dict],
    current_state: dict[str, dict],
    anomaly_alerts: list[dict] | None = None,
) -> OperatorAnswer:
    """Ask the Gemini copilot a question.

    Args:
        question: The operator's question
        history: Conversation history [{"role": "user"|"model", "content": "..."}]
        decisions: Recent coordination decisions
        robot_states: Historical robot states by robot_id
        zone_states: Current zone states by zone_id
        current_state: Current state of all entities
        anomaly_alerts: Recent anomaly alerts from Flink AI pipeline

    Returns:
        Structured answer with evidence and tool call log
    """
    client = get_client()
    if client is None:
        return OperatorAnswer(
            summary="Gemini is not configured. Set GOOGLE_CLOUD_PROJECT for Vertex AI or GOOGLE_API_KEY for API key auth.",
            confidence="INSUFFICIENT",
            error="Client not configured",
        )

    # Set context for tool functions
    set_tool_context(ToolContext(
        decisions=decisions,
        robot_states=robot_states,
        zone_states=zone_states,
        current_state=current_state,
        anomaly_alerts=anomaly_alerts or [],
        simulator_url=settings.simulator_url,
    ))

    # Build conversation contents with history
    contents = []
    for msg in history:
        contents.append(types.Content(
            role=msg["role"],
            parts=[types.Part(text=msg["content"])],
        ))
    # Add current question
    contents.append(types.Content(
        role="user",
        parts=[types.Part(text=question)],
    ))

    def _call_gemini():
        """Synchronous Gemini call to run in thread pool."""
        return client.models.generate_content(
            model=settings.gemini_model,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                tools=TOOLS,
                automatic_function_calling=types.AutomaticFunctionCallingConfig(
                    maximum_remote_calls=10,
                ),
            ),
        )

    try:
        # Run blocking Gemini call in thread pool to avoid blocking the event loop
        response = await asyncio.to_thread(_call_gemini)

        # Extract tool calls from response (for logging)
        tool_calls = []
        if hasattr(response, 'automatic_function_calling_history') and response.automatic_function_calling_history:
            for entry in response.automatic_function_calling_history:
                if hasattr(entry, 'parts') and entry.parts:
                    for part in entry.parts:
                        fc = getattr(part, 'function_call', None)
                        if fc and hasattr(fc, 'name') and fc.name:
                            tool_calls.append(ToolCallLog(
                                tool=fc.name,
                                params=dict(fc.args) if fc.args else {},
                                success=True,
                            ))

        # Get the text response
        answer_text = response.text if response.text else "No response generated."

        return OperatorAnswer(
            summary=answer_text,
            confidence="HIGH" if tool_calls else "MEDIUM",
            tool_calls=tool_calls,
        )

    except Exception as e:
        logger.error(f"Gemini error: {e}")
        return OperatorAnswer(
            summary=f"Error: {str(e)}",
            confidence="INSUFFICIENT",
            error=str(e),
        )


async def ask_copilot_stream(
    question: str,
    history: list[dict],
    decisions: list[dict],
    robot_states: dict[str, list[dict]],
    zone_states: dict[str, dict],
    current_state: dict[str, dict],
    anomaly_alerts: list[dict] | None = None,
) -> AsyncIterator[str]:
    """Stream responses from Gemini copilot.

    Yields SSE-formatted events:
    - {"type": "tool", "name": "...", "params": {...}}
    - {"type": "chunk", "text": "..."}
    - {"type": "done", "confidence": "HIGH"}
    - {"type": "error", "message": "..."}
    """
    client = get_client()
    if client is None:
        yield json.dumps({"type": "error", "message": "Gemini not configured"})
        return

    # Set context for tool functions
    set_tool_context(ToolContext(
        decisions=decisions,
        robot_states=robot_states,
        zone_states=zone_states,
        current_state=current_state,
        anomaly_alerts=anomaly_alerts or [],
        simulator_url=settings.simulator_url,
    ))

    # Build conversation contents with history
    contents = []
    for msg in history:
        contents.append(types.Content(
            role=msg["role"],
            parts=[types.Part(text=msg["content"])],
        ))
    contents.append(types.Content(
        role="user",
        parts=[types.Part(text=question)],
    ))

    tool_calls = []

    def _call_gemini_stream():
        """Synchronous streaming Gemini call."""
        return client.models.generate_content_stream(
            model=settings.gemini_model,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                tools=TOOLS,
                automatic_function_calling=types.AutomaticFunctionCallingConfig(
                    maximum_remote_calls=10,
                ),
            ),
        )

    try:
        # Get the streaming response iterator in thread
        stream = await asyncio.to_thread(_call_gemini_stream)

        # Use a queue for true streaming between thread and async generator
        import queue
        event_queue: queue.Queue = queue.Queue()

        def _consume_stream():
            """Consume the stream in a thread, pushing events to queue."""
            seen_tools = set()

            for chunk in stream:
                # Extract tool calls if present
                if hasattr(chunk, 'automatic_function_calling_history') and chunk.automatic_function_calling_history:
                    for entry in chunk.automatic_function_calling_history:
                        if hasattr(entry, 'parts') and entry.parts:
                            for part in entry.parts:
                                fc = getattr(part, 'function_call', None)
                                if fc and hasattr(fc, 'name') and fc.name and fc.name not in seen_tools:
                                    seen_tools.add(fc.name)
                                    event_queue.put({"type": "tool", "name": fc.name})

                # Extract text from chunk candidates
                try:
                    if chunk.candidates:
                        for candidate in chunk.candidates:
                            if candidate.content and candidate.content.parts:
                                for part in candidate.content.parts:
                                    if hasattr(part, 'text') and part.text:
                                        event_queue.put({"type": "chunk", "text": part.text})
                except Exception:
                    # Fallback: try chunk.text directly
                    if hasattr(chunk, 'text') and chunk.text:
                        event_queue.put({"type": "chunk", "text": chunk.text})

            event_queue.put({"type": "done", "has_tools": len(seen_tools) > 0})

        # Start consuming in background thread
        import threading
        thread = threading.Thread(target=_consume_stream)
        thread.start()

        # Yield events as they arrive
        while True:
            try:
                event = event_queue.get(timeout=0.1)
                if event["type"] == "done":
                    confidence = "HIGH" if event.get("has_tools") else "MEDIUM"
                    yield json.dumps({"type": "done", "confidence": confidence})
                    break
                yield json.dumps(event)
            except queue.Empty:
                if not thread.is_alive():
                    break
                await asyncio.sleep(0.05)

        thread.join()

    except Exception as e:
        logger.error(f"Gemini streaming error: {e}")
        yield json.dumps({"type": "error", "message": str(e)})
