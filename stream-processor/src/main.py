"""Main stream processor using QuixStreams."""

import atexit
import json
import logging
import math
import time
from collections import defaultdict

import httpx
from quixstreams import Application
from quixstreams.models.topics import TopicConfig

from .config import settings
from .risk import assess_risk, create_decision_event, Action

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# HTTP client for applying decisions to simulator
http_client: httpx.Client | None = None


def cleanup_http_client():
    """Clean up HTTP client on exit."""
    global http_client
    if http_client is not None:
        http_client.close()
        http_client = None


atexit.register(cleanup_http_client)


def get_http_client() -> httpx.Client:
    """Get or create HTTP client for simulator communication."""
    global http_client
    if http_client is None:
        http_client = httpx.Client(timeout=2.0)
    return http_client


def apply_decision_to_simulator(decision: dict) -> bool:
    """POST decision to simulator to apply it."""
    if not settings.apply_decisions:
        return True

    try:
        client = get_http_client()
        response = client.post(
            f"{settings.simulator_url}/decision",
            json={
                "robot_id": decision["robot_id"],
                "action": decision["action"],
            },
        )
        if response.status_code == 200:
            logger.debug(f"Applied decision: {decision['robot_id']} -> {decision['action']}")
            return True
        else:
            logger.warning(f"Failed to apply decision: {response.status_code}")
            return False
    except httpx.RequestError as e:
        logger.warning(f"Could not reach simulator: {e}")
        return False


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

        # Apply decision to simulator
        apply_decision_to_simulator(decision)

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
    if settings.apply_decisions:
        logger.info(f"Decision application enabled -> {settings.simulator_url}")
    else:
        logger.info("Decision application disabled (Kafka-only mode)")

    # Build QuixStreams Application with optional SASL config
    app_kwargs = {
        "broker_address": settings.kafka_brokers,
        "consumer_group": settings.prefixed_consumer_group,
        "auto_offset_reset": "latest",
    }

    # Add Confluent Cloud auth if configured
    if settings.kafka_api_key and settings.kafka_api_secret:
        logger.info("Using Confluent Cloud authentication")
        from quixstreams.kafka.configuration import ConnectionConfig
        app_kwargs["broker_address"] = ConnectionConfig(
            bootstrap_servers=settings.kafka_brokers,
            security_protocol=settings.kafka_security_protocol or "SASL_SSL",
            sasl_mechanism=settings.kafka_sasl_mechanism or "PLAIN",
            sasl_username=settings.kafka_api_key,
            sasl_password=settings.kafka_api_secret,
        )

    app = Application(**app_kwargs)

    # Topic config - Confluent Cloud requires replication_factor=3
    topic_config = None
    if settings.kafka_api_key and settings.kafka_api_secret:
        topic_config = TopicConfig(num_partitions=1, replication_factor=3)

    # Input topics (with prefix support)
    robot_topic = app.topic(settings.topic(settings.robot_telemetry_topic), value_deserializer="json", config=topic_config)
    human_topic = app.topic(settings.topic(settings.human_telemetry_topic), value_deserializer="json", config=topic_config)
    zone_topic = app.topic(settings.topic(settings.zone_context_topic), value_deserializer="json", config=topic_config)

    # Output topics (with prefix support)
    decisions_topic = app.topic(settings.topic(settings.coordination_decisions_topic), value_serializer="json", config=topic_config)
    state_topic = app.topic(settings.topic(settings.coordination_state_topic), value_serializer="json", config=topic_config)

    # Process robot telemetry -> state + decisions
    sdf_robots = app.dataframe(robot_topic)

    # Process each robot update: emit state and optionally a decision
    def process_and_emit(value: dict) -> dict:
        """Update state, create coordination state, and check for decisions."""
        state.update_robot(value)
        coord_state = create_coordination_state(value)
        decision = process_robot_telemetry(value)
        # Return both, we'll handle them in the pipeline
        return {"state": coord_state, "decision": decision}

    sdf_robots = sdf_robots.apply(process_and_emit)

    # Emit coordination state for every update
    sdf_state = sdf_robots.apply(lambda v: v["state"])
    sdf_state.to_topic(state_topic)

    # Emit decisions only when present
    sdf_decisions = sdf_robots.apply(lambda v: v["decision"])
    sdf_decisions = sdf_decisions.filter(lambda v: v is not None)
    sdf_decisions.to_topic(decisions_topic)

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
