"""
Pytest fixtures for integration tests.

PREREQUISITES:
  These tests require the simulator package to be installed.

  Setup:
    cd simulator
    uv pip install -e ".[dev]"
    # or: pip install -e ".[dev]"

  Run integration tests:
    pytest tests/integration/ -v
"""

import random

import pytest

from src.entities import Robot, Human, Zone
from src.world import World


@pytest.fixture
def mock_world():
    """Create a mock world for API testing (no Kafka)."""
    return World(
        zone=Zone(zone_id="test-zone", width=50.0, height=30.0),
        robots=[
            Robot(robot_id="robot-1", zone_id="test-zone", x=10.0, y=10.0),
            Robot(robot_id="robot-2", zone_id="test-zone", x=40.0, y=20.0),
        ],
        humans=[
            Human(human_id="human-1", zone_id="test-zone", x=15.0, y=15.0),
        ],
        rng=random.Random(42),
        producer=None,
    )
