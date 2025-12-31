"""Telemetry event schemas emitted by the simulator."""

from pydantic import BaseModel, Field
from typing import Literal


class RobotTelemetry(BaseModel):
    """Real-time robot state from the simulator."""

    robot_id: str = Field(..., description="Unique robot identifier (e.g., 'robot-1')")
    timestamp: int = Field(..., description="Unix timestamp in milliseconds")

    # Position and motion
    x: float = Field(..., description="X coordinate in meters")
    y: float = Field(..., description="Y coordinate in meters")
    velocity: float = Field(..., ge=0, description="Current speed in m/s")
    heading: float = Field(..., ge=0, lt=360, description="Heading in degrees (0-359)")
    motion_state: Literal["moving", "stopped", "slowing"] = Field(
        ..., description="Current motion state"
    )

    # Sensors
    ultrasonic_distance: float | None = Field(
        None, ge=0, description="Nearest obstacle distance in meters (ultrasonic)"
    )
    ble_rssi: float | None = Field(
        None, description="BLE signal strength (dBm), indicates human proximity"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "robot_id": "robot-1",
                "timestamp": 1703001234567,
                "x": 12.5,
                "y": 8.3,
                "velocity": 1.2,
                "heading": 45.0,
                "motion_state": "moving",
                "ultrasonic_distance": 3.5,
                "ble_rssi": -65.0,
            }
        }


class HumanTelemetry(BaseModel):
    """Human position from BLE beacons or vision system."""

    human_id: str = Field(..., description="Unique human identifier (e.g., 'human-1')")
    timestamp: int = Field(..., description="Unix timestamp in milliseconds")

    # Position (may be less precise than robot)
    x: float = Field(..., description="X coordinate in meters")
    y: float = Field(..., description="Y coordinate in meters")
    velocity: float = Field(..., ge=0, description="Estimated speed in m/s")
    heading: float | None = Field(None, description="Heading in degrees if known")

    # Confidence
    position_confidence: float = Field(
        ..., ge=0, le=1, description="Position estimate confidence (0-1)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "human_id": "human-1",
                "timestamp": 1703001234567,
                "x": 10.0,
                "y": 7.5,
                "velocity": 0.8,
                "heading": 90.0,
                "position_confidence": 0.85,
            }
        }
