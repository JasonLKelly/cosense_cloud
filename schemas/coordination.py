"""Coordination decision schemas emitted by the stream processor."""

from enum import Enum
from pydantic import BaseModel, Field


class Action(str, Enum):
    """Coordination action commands."""

    CONTINUE = "CONTINUE"  # No intervention needed
    SLOW = "SLOW"  # Reduce speed
    STOP = "STOP"  # Full stop
    REROUTE = "REROUTE"  # Find alternate path


class ReasonCode(str, Enum):
    """Reason codes explaining why a decision was made."""

    NONE = "NONE"  # No special condition
    CLOSE_PROXIMITY = "CLOSE_PROXIMITY"  # Human too close
    HIGH_RELATIVE_SPEED = "HIGH_RELATIVE_SPEED"  # Closing speed too fast
    LOW_VISIBILITY = "LOW_VISIBILITY"  # Vision system degraded
    HIGH_CONGESTION = "HIGH_CONGESTION"  # Zone too crowded
    BLE_PROXIMITY_DETECTED = "BLE_PROXIMITY_DETECTED"  # BLE indicates nearby human
    SENSOR_DISAGREEMENT = "SENSOR_DISAGREEMENT"  # Sensors give conflicting readings


class CoordinationState(BaseModel):
    """Fused state for a robot with nearby context."""

    robot_id: str = Field(..., description="Robot identifier")
    timestamp: int = Field(..., description="Unix timestamp in milliseconds")
    zone_id: str = Field(..., description="Current zone")

    # Robot state
    x: float
    y: float
    velocity: float
    heading: float
    motion_state: str

    # Nearest human (if any)
    nearest_human_id: str | None = Field(None, description="ID of nearest human")
    nearest_human_distance: float | None = Field(
        None, ge=0, description="Distance to nearest human in meters"
    )
    relative_velocity: float | None = Field(
        None, description="Closing speed with nearest human (positive = approaching)"
    )

    # Zone context
    visibility: str
    congestion_level: float
    connectivity: str

    # Risk assessment
    risk_score: float = Field(
        ..., ge=0, le=1, description="Computed risk score (0=safe, 1=critical)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "robot_id": "robot-1",
                "timestamp": 1703001234567,
                "zone_id": "zone-c",
                "x": 12.5,
                "y": 8.3,
                "velocity": 1.2,
                "heading": 45.0,
                "motion_state": "moving",
                "nearest_human_id": "human-1",
                "nearest_human_distance": 2.5,
                "relative_velocity": 0.8,
                "visibility": "normal",
                "congestion_level": 0.3,
                "connectivity": "normal",
                "risk_score": 0.45,
            }
        }


class CoordinationDecision(BaseModel):
    """A coordination decision for a robot."""

    decision_id: str = Field(..., description="Unique decision identifier")
    robot_id: str = Field(..., description="Robot this decision applies to")
    timestamp: int = Field(..., description="Unix timestamp in milliseconds")
    zone_id: str = Field(..., description="Zone where decision was made")

    # Decision
    action: Action = Field(..., description="Commanded action")
    reason_codes: list[ReasonCode] = Field(
        ..., description="All contributing reasons"
    )
    primary_reason: ReasonCode = Field(..., description="Primary reason for action")

    # Context snapshot (for explainability)
    risk_score: float = Field(..., ge=0, le=1, description="Risk score at decision time")
    nearest_human_distance: float | None = Field(
        None, description="Distance to nearest human at decision time"
    )
    triggering_event: str | None = Field(
        None, description="What triggered this decision (e.g., 'human entered zone')"
    )

    # For UI
    summary: str = Field(
        ..., description="Human-readable one-line summary"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "decision_id": "dec-1703001234567-robot-1",
                "robot_id": "robot-1",
                "timestamp": 1703001234567,
                "zone_id": "zone-c",
                "action": "SLOW",
                "reason_codes": ["CLOSE_PROXIMITY", "HIGH_RELATIVE_SPEED"],
                "primary_reason": "CLOSE_PROXIMITY",
                "risk_score": 0.65,
                "nearest_human_distance": 2.5,
                "triggering_event": "Human approaching at high relative speed",
                "summary": "Robot-1 slowing: human within 2.5m and closing",
            }
        }
