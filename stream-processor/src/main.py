"""Main stream processor using QuixStreams."""

import json
import logging
import math
import time
from collections import defaultdict

from quixstreams import Application

from .config import settings
from .risk import assess_risk, create_decision_event, Action

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# In-memory state for windowed joins
# In production, QuixStreams would handle this with RocksDB
class StateStore:
    """Simple in-memory state for robot/human/zone data."""

    def __init__(self):
        self.robots: dict[str, dict] = {}  # robot_id -> latest telemetry
        self.humans: dict[str, dict] = {}  # human_id -> latest telemetry
        self.zones: dict[str, dict] = {}   # zone_id -> latest context
        self.last_decisions: dict[str, dict] = {}  # robot_id -> last decision
        self.last_emit_time: float = 0

    def update_robot(self, data: dict):
        self.robots[data["robot_id"]] = data

    def update_human(self, data: dict):
        self.humans[data["human_id"]] = data

    def update_zone(self, data: dict):
        self.zones[data["zone_id"]] = data

    def get_nearest_human(self, robot: dict) -> dict | None:
        """Find nearest human to a robot."""
        if not self.humans:
            return None

        min_dist = float("inf")
        nearest = None

        for human in self.humans.values():
            if human.get("zone_id") != robot.get("zone_id"):
                continue
            dist = math.sqrt(
                (human["x"] - robot["x"]) ** 2 +
                (human["y"] - robot["y"]) ** 2
            )
            if dist < min_dist:
                min_dist = dist
                nearest = human

        return nearest

    def get_zone(self, zone_id: str) -> dict | None:
        return self.zones.get(zone_id)

    def should_emit(self) -> bool:
        """Check if enough time has passed to emit state."""
        now = time.time() * 1000
        if now - self.last_emit_time >= settings.state_emit_interval_ms:
            self.last_emit_time = now
            return True
        return False

    def decision_changed(self, robot_id: str, new_action: Action) -> bool:
        """Check if decision changed from last time."""
        last = self.last_decisions.get(robot_id)
        if not last:
            return True
        return last.get("action") != new_action.value


state = StateStore()


def process_robot_telemetry(value: dict) -> dict | None:
    """Process robot telemetry and potentially emit decisions."""
    state.update_robot(value)

    robot_id = value["robot_id"]
    zone_id = value.get("zone_id", "zone-c")

    # Find nearest human and zone context
    nearest_human = state.get_nearest_human(value)
    zone = state.get_zone(zone_id)

    # Assess risk
    assessment = assess_risk(value, nearest_human, zone)

    # Only emit decision if action changed or is not CONTINUE
    if assessment.action != Action.CONTINUE or state.decision_changed(robot_id, assessment.action):
        decision = create_decision_event(assessment, zone_id)
        state.last_decisions[robot_id] = decision
        return decision

    return None


def process_human_telemetry(value: dict) -> None:
    """Process human telemetry (just update state)."""
    state.update_human(value)


def process_zone_context(value: dict) -> None:
    """Process zone context (just update state)."""
    state.update_zone(value)


def create_coordination_state(robot: dict) -> dict:
    """Create coordination state event for a robot."""
    nearest_human = state.get_nearest_human(robot)
    zone = state.get_zone(robot.get("zone_id", "zone-c"))

    nearest_human_distance = None
    relative_velocity = None
    nearest_human_id = None

    if nearest_human:
        nearest_human_id = nearest_human["human_id"]
        nearest_human_distance = math.sqrt(
            (nearest_human["x"] - robot["x"]) ** 2 +
            (nearest_human["y"] - robot["y"]) ** 2
        )
        # Simplified relative velocity (just magnitude difference for now)
        relative_velocity = robot.get("velocity", 0) + nearest_human.get("velocity", 0)

    assessment = assess_risk(robot, nearest_human, zone)

    return {
        "robot_id": robot["robot_id"],
        "timestamp": int(time.time() * 1000),
        "zone_id": robot.get("zone_id", "zone-c"),
        "x": robot["x"],
        "y": robot["y"],
        "velocity": robot["velocity"],
        "heading": robot["heading"],
        "motion_state": robot["motion_state"],
        "nearest_human_id": nearest_human_id,
        "nearest_human_distance": round(nearest_human_distance, 2) if nearest_human_distance else None,
        "relative_velocity": round(relative_velocity, 2) if relative_velocity else None,
        "visibility": zone.get("visibility", "normal") if zone else "normal",
        "congestion_level": zone.get("congestion_level", 0) if zone else 0,
        "connectivity": zone.get("connectivity", "normal") if zone else "normal",
        "risk_score": assessment.risk_score,
    }


def main():
    """Main entry point."""
    logger.info("Starting CoSense Stream Processor")
    logger.info(f"Kafka brokers: {settings.kafka_brokers}")

    # Build QuixStreams Application with optional SASL config
    app_kwargs = {
        "broker_address": settings.kafka_brokers,
        "consumer_group": settings.consumer_group,
        "auto_offset_reset": "latest",
    }

    # Add Confluent Cloud auth if configured
    if settings.kafka_api_key and settings.kafka_api_secret:
        logger.info("Using Confluent Cloud authentication")
        app_kwargs["broker_address"] = {
            "bootstrap.servers": settings.kafka_brokers,
            "security.protocol": settings.kafka_security_protocol or "SASL_SSL",
            "sasl.mechanism": settings.kafka_sasl_mechanism or "PLAIN",
            "sasl.username": settings.kafka_api_key,
            "sasl.password": settings.kafka_api_secret,
        }

    app = Application(**app_kwargs)

    # Input topics
    robot_topic = app.topic(settings.robot_telemetry_topic, value_deserializer="json")
    human_topic = app.topic(settings.human_telemetry_topic, value_deserializer="json")
    zone_topic = app.topic(settings.zone_context_topic, value_deserializer="json")

    # Output topics
    decisions_topic = app.topic(settings.coordination_decisions_topic, value_serializer="json")
    state_topic = app.topic(settings.coordination_state_topic, value_serializer="json")

    # Process robot telemetry -> decisions
    sdf_robots = app.dataframe(robot_topic)

    # Update state and emit decisions
    sdf_robots = sdf_robots.apply(
        lambda value: (
            state.update_robot(value),
            process_robot_telemetry(value),
        )[1]  # Return just the decision (or None)
    )

    # Filter out None (no decision to emit)
    sdf_robots = sdf_robots.filter(lambda value: value is not None)

    # Produce decisions
    sdf_robots.to_topic(decisions_topic)

    # Also emit coordination state periodically
    # Note: In a real QuixStreams app, you'd use windowed aggregations
    # For simplicity, we emit state with each robot update

    # Process human telemetry (just update state)
    sdf_humans = app.dataframe(human_topic)
    sdf_humans.apply(lambda value: state.update_human(value))

    # Process zone context (just update state)
    sdf_zones = app.dataframe(zone_topic)
    sdf_zones.apply(lambda value: state.update_zone(value))

    logger.info("Stream processor configured, starting...")
    app.run()


if __name__ == "__main__":
    main()
