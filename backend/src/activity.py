"""Pipeline activity tracking for real-time observability."""

import asyncio
import time
from collections import deque
from enum import Enum
from typing import Any

from pydantic import BaseModel


class ActivityType(str, Enum):
    """Types of pipeline activity events."""
    TOOL_CALL = "tool_call"
    DECISION = "decision"
    ANOMALY = "anomaly"


class ActivityEvent(BaseModel):
    """A pipeline activity event."""
    type: ActivityType
    timestamp_ms: int
    data: dict[str, Any]


class ActivityBuffer:
    """Thread-safe buffer for pipeline activity events with pub/sub."""

    def __init__(self, maxlen: int = 200):
        self._events: deque[ActivityEvent] = deque(maxlen=maxlen)
        self._subscribers: list[asyncio.Queue] = []
        self._lock = asyncio.Lock()

    async def add_event(self, event: ActivityEvent):
        """Add an event and notify all subscribers."""
        async with self._lock:
            self._events.append(event)
            # Notify all subscribers
            for queue in self._subscribers:
                try:
                    queue.put_nowait(event)
                except asyncio.QueueFull:
                    pass  # Drop if subscriber is slow

    async def subscribe(self) -> asyncio.Queue:
        """Subscribe to activity events. Returns a queue that receives events."""
        queue: asyncio.Queue = asyncio.Queue(maxsize=100)
        async with self._lock:
            self._subscribers.append(queue)
        return queue

    async def unsubscribe(self, queue: asyncio.Queue):
        """Unsubscribe from activity events."""
        async with self._lock:
            if queue in self._subscribers:
                self._subscribers.remove(queue)

    def get_recent(self, limit: int = 50) -> list[ActivityEvent]:
        """Get recent events (most recent last)."""
        return list(self._events)[-limit:]


# Module-level singleton
activity_buffer = ActivityBuffer()


def emit_tool_call(tool_name: str, params: dict[str, Any], question_id: str = ""):
    """Helper to emit a tool call event (sync, schedules async)."""
    event = ActivityEvent(
        type=ActivityType.TOOL_CALL,
        timestamp_ms=int(time.time() * 1000),
        data={
            "tool_name": tool_name,
            "params": params,
            "question_id": question_id,
        },
    )
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(activity_buffer.add_event(event))
    except RuntimeError:
        # No event loop running, skip
        pass


async def emit_decision(robot_id: str, action: str, reason_codes: list[str], risk_score: float):
    """Emit a decision event."""
    event = ActivityEvent(
        type=ActivityType.DECISION,
        timestamp_ms=int(time.time() * 1000),
        data={
            "robot_id": robot_id,
            "action": action,
            "reason_codes": reason_codes,
            "risk_score": risk_score,
        },
    )
    await activity_buffer.add_event(event)


async def emit_anomaly(
    alert_type: str,
    severity: str,
    zone_id: str,
    robot_id: str | None,
    actual_value: float,
    forecast_value: float,
):
    """Emit an anomaly detection event."""
    deviation = ((actual_value - forecast_value) / forecast_value * 100) if forecast_value else 0
    event = ActivityEvent(
        type=ActivityType.ANOMALY,
        timestamp_ms=int(time.time() * 1000),
        data={
            "alert_type": alert_type,
            "severity": severity,
            "zone_id": zone_id,
            "robot_id": robot_id,
            "actual_value": actual_value,
            "forecast_value": forecast_value,
            "deviation_percent": round(deviation, 1),
        },
    )
    await activity_buffer.add_event(event)
