"""Risk scoring and decision logic."""

import math
import uuid
import time
from dataclasses import dataclass
from enum import Enum

from .config import settings


class Action(str, Enum):
    CONTINUE = "CONTINUE"
    SLOW = "SLOW"
    STOP = "STOP"
    REROUTE = "REROUTE"


class ReasonCode(str, Enum):
    NONE = "NONE"
    CLOSE_PROXIMITY = "CLOSE_PROXIMITY"
    HIGH_RELATIVE_SPEED = "HIGH_RELATIVE_SPEED"
    BLE_PROXIMITY_DETECTED = "BLE_PROXIMITY_DETECTED"
    SENSOR_DISAGREEMENT = "SENSOR_DISAGREEMENT"


@dataclass
class RiskAssessment:
    """Result of risk assessment for a robot."""

    robot_id: str
    risk_score: float  # 0.0 - 1.0
    action: Action
    reason_codes: list[ReasonCode]
    primary_reason: ReasonCode
    nearest_human_distance: float | None
    relative_velocity: float | None
    summary: str


def calculate_distance(x1: float, y1: float, x2: float, y2: float) -> float:
    """Euclidean distance."""
    return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)


def calculate_relative_velocity(
    robot_x: float, robot_y: float, robot_vx: float, robot_vy: float,
    human_x: float, human_y: float, human_vx: float, human_vy: float,
) -> float:
    """
    Calculate relative velocity (closing speed).
    Positive = approaching, negative = separating.
    """
    # Direction vector from robot to human
    dx = human_x - robot_x
    dy = human_y - robot_y
    dist = math.sqrt(dx * dx + dy * dy)
    if dist < 0.01:
        return 0.0

    # Normalize
    nx, ny = dx / dist, dy / dist

    # Relative velocity components
    rel_vx = robot_vx - human_vx
    rel_vy = robot_vy - human_vy

    # Closing speed = projection of relative velocity onto direction vector
    return rel_vx * nx + rel_vy * ny


def velocity_components(velocity: float, heading_deg: float) -> tuple[float, float]:
    """Convert velocity + heading to vx, vy."""
    heading_rad = math.radians(heading_deg)
    return velocity * math.cos(heading_rad), velocity * math.sin(heading_rad)


def assess_risk(
    robot: dict,
    nearest_human: dict | None,
) -> RiskAssessment:
    """
    Assess risk for a robot and determine action.

    Risk score formula (weighted sum, capped at 1.0):
    - Proximity: 0.45 weight (inverse of distance)
    - Relative speed: 0.30 weight
    - BLE proximity: 0.15 weight
    - Sensor disagreement: 0.10 weight
    """
    reason_codes: list[ReasonCode] = []
    risk_components: dict[str, float] = {}

    # Defaults
    nearest_distance: float | None = None
    relative_vel: float | None = None

    # 1. Proximity risk
    if nearest_human:
        dist = calculate_distance(
            robot["x"], robot["y"],
            nearest_human["x"], nearest_human["y"]
        )
        nearest_distance = dist

        if dist < settings.proximity_critical_m:
            risk_components["proximity"] = 1.0
            reason_codes.append(ReasonCode.CLOSE_PROXIMITY)
        elif dist < settings.proximity_warning_m:
            # Linear interpolation
            risk_components["proximity"] = (settings.proximity_warning_m - dist) / (
                settings.proximity_warning_m - settings.proximity_critical_m
            )
            reason_codes.append(ReasonCode.CLOSE_PROXIMITY)
        else:
            risk_components["proximity"] = 0.0

        # 2. Relative velocity risk
        robot_vx, robot_vy = velocity_components(robot["velocity"], robot["heading"])
        human_heading = nearest_human.get("heading") or 0
        human_vx, human_vy = velocity_components(
            nearest_human.get("velocity", 0), human_heading
        )

        relative_vel = calculate_relative_velocity(
            robot["x"], robot["y"], robot_vx, robot_vy,
            nearest_human["x"], nearest_human["y"], human_vx, human_vy,
        )

        if relative_vel > settings.speed_warning_ms:
            risk_components["relative_speed"] = min(1.0, relative_vel / 3.0)
            reason_codes.append(ReasonCode.HIGH_RELATIVE_SPEED)
        else:
            risk_components["relative_speed"] = 0.0
    else:
        risk_components["proximity"] = 0.0
        risk_components["relative_speed"] = 0.0

    # 3. BLE proximity (sensor-based, independent check)
    ble_rssi = robot.get("ble_rssi")
    if ble_rssi is not None and ble_rssi > -60:  # Strong signal = close
        risk_components["ble"] = min(1.0, (-ble_rssi - 40) / 20)
        if ReasonCode.CLOSE_PROXIMITY not in reason_codes:
            reason_codes.append(ReasonCode.BLE_PROXIMITY_DETECTED)
    else:
        risk_components["ble"] = 0.0

    # 4. Sensor disagreement
    # If ultrasonic says clear but BLE says close (or vice versa)
    ultrasonic = robot.get("ultrasonic_distance")
    if ultrasonic is not None and ble_rssi is not None:
        ultrasonic_says_close = ultrasonic < settings.proximity_warning_m
        ble_says_close = ble_rssi > -65

        if ultrasonic_says_close != ble_says_close:
            risk_components["sensor_disagreement"] = 0.5
            reason_codes.append(ReasonCode.SENSOR_DISAGREEMENT)
        else:
            risk_components["sensor_disagreement"] = 0.0
    else:
        risk_components["sensor_disagreement"] = 0.0

    # Calculate weighted risk score
    weights = {
        "proximity": 0.45,
        "relative_speed": 0.30,
        "ble": 0.15,
        "sensor_disagreement": 0.10,
    }

    risk_score = sum(
        risk_components.get(k, 0) * w for k, w in weights.items()
    )
    risk_score = min(1.0, risk_score)

    # Determine action
    if risk_score >= 0.7:
        action = Action.STOP
    elif risk_score >= 0.4:
        action = Action.SLOW
    else:
        action = Action.CONTINUE

    # Primary reason (highest weighted contributor)
    if not reason_codes:
        reason_codes = [ReasonCode.NONE]

    primary_reason = reason_codes[0]  # First added is usually most significant

    # Generate summary
    summary = generate_summary(robot["robot_id"], action, reason_codes, nearest_distance)

    return RiskAssessment(
        robot_id=robot["robot_id"],
        risk_score=round(risk_score, 3),
        action=action,
        reason_codes=reason_codes,
        primary_reason=primary_reason,
        nearest_human_distance=round(nearest_distance, 2) if nearest_distance else None,
        relative_velocity=round(relative_vel, 2) if relative_vel else None,
        summary=summary,
    )


def generate_summary(
    robot_id: str,
    action: Action,
    reason_codes: list[ReasonCode],
    distance: float | None,
) -> str:
    """Generate human-readable summary of the decision."""
    if action == Action.CONTINUE:
        return f"{robot_id} proceeding normally"

    action_verb = {
        Action.SLOW: "slowing",
        Action.STOP: "stopping",
        Action.REROUTE: "rerouting",
    }[action]

    reasons = []
    for code in reason_codes[:2]:  # Max 2 reasons in summary
        if code == ReasonCode.CLOSE_PROXIMITY:
            reasons.append(f"human within {distance:.1f}m" if distance else "human nearby")
        elif code == ReasonCode.HIGH_RELATIVE_SPEED:
            reasons.append("high closing speed")
        elif code == ReasonCode.BLE_PROXIMITY_DETECTED:
            reasons.append("BLE proximity alert")
        elif code == ReasonCode.SENSOR_DISAGREEMENT:
            reasons.append("sensor readings conflict")

    reason_str = " and ".join(reasons) if reasons else "precautionary"
    return f"{robot_id} {action_verb}: {reason_str}"


def create_decision_event(assessment: RiskAssessment) -> dict:
    """Create a coordination decision event from assessment."""
    return {
        "decision_id": f"dec-{int(time.time() * 1000)}-{assessment.robot_id}",
        "robot_id": assessment.robot_id,
        "timestamp": int(time.time() * 1000),
        "action": assessment.action.value,
        "reason_codes": [r.value for r in assessment.reason_codes],
        "primary_reason": assessment.primary_reason.value,
        "risk_score": assessment.risk_score,
        "nearest_human_distance": assessment.nearest_human_distance,
        "triggering_event": None,  # Could be enhanced to track what changed
        "summary": assessment.summary,
    }
