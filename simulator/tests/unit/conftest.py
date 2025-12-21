"""Pytest fixtures for unit tests - no external dependencies."""

import random

import pytest

from src.entities import Robot, Human, Zone
from src.world import World


@pytest.fixture
def rng() -> random.Random:
    """Deterministic random number generator for reproducible tests."""
    return random.Random(42)


@pytest.fixture
def zone() -> Zone:
    """Create a test zone with default dimensions."""
    return Zone(
        zone_id="test-zone",
        width=50.0,
        height=30.0,
    )


@pytest.fixture
def robot(zone: Zone) -> Robot:
    """Create a test robot at center of zone."""
    return Robot(
        robot_id="test-robot-1",
        zone_id=zone.zone_id,
        x=zone.width / 2,
        y=zone.height / 2,
    )


@pytest.fixture
def human(zone: Zone) -> Human:
    """Create a test human at center of zone."""
    return Human(
        human_id="test-human-1",
        zone_id=zone.zone_id,
        x=zone.width / 2,
        y=zone.height / 2,
    )


@pytest.fixture
def world() -> World:
    """Create a test world without Kafka (no external dependencies)."""
    return World(
        zone=Zone(zone_id="test-zone", width=50.0, height=30.0),
        robots=[
            Robot(robot_id="robot-1", zone_id="test-zone", x=10.0, y=10.0),
            Robot(robot_id="robot-2", zone_id="test-zone", x=40.0, y=20.0),
        ],
        humans=[
            Human(human_id="human-1", zone_id="test-zone", x=15.0, y=15.0),
            Human(human_id="human-2", zone_id="test-zone", x=35.0, y=25.0),
        ],
        rng=random.Random(42),
        producer=None,  # No Kafka - unit test
    )


@pytest.fixture
def world_close_proximity() -> World:
    """Create a world where robot and human are very close (2m)."""
    return World(
        zone=Zone(zone_id="test-zone", width=50.0, height=30.0),
        robots=[
            Robot(robot_id="robot-1", zone_id="test-zone", x=10.0, y=10.0),
        ],
        humans=[
            Human(human_id="human-1", zone_id="test-zone", x=12.0, y=10.0),
        ],
        rng=random.Random(42),
        producer=None,
    )
