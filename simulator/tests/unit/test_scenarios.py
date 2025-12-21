"""
Demo scenarios as unit tests - no external dependencies.

These tests demonstrate key behaviors of the simulation system
using pure Python - no Kafka, no HTTP, no external services.

Run with: pytest tests/unit/test_scenarios.py -v
"""

import random
import pytest

from src.entities import Robot, Human, Zone
from src.world import World


class TestScenario_RobotStopsForHuman:
    """
    SCENARIO: Robot stops when commanded due to human proximity.

    Demonstrates the core safety behavior where coordination
    commands a robot to stop when a human is detected nearby.
    """

    def test_robot_decelerates_smoothly(self):
        """Robot smoothly decelerates when STOP is commanded."""
        world = World(
            zone=Zone(zone_id="zone-c", width=50.0, height=30.0),
            robots=[Robot(robot_id="robot-1", zone_id="zone-c", x=10.0, y=10.0)],
            humans=[Human(human_id="human-1", zone_id="zone-c", x=12.0, y=10.0)],
            rng=random.Random(42),
            producer=None,
        )

        robot = world.robots[0]
        robot.target_x = 30.0
        robot.target_y = 10.0
        robot.velocity = 2.0
        robot.motion_state = "moving"

        world.apply_decision("robot-1", "STOP")

        velocities = [robot.velocity]
        for _ in range(20):
            world.tick(0.1)
            velocities.append(robot.velocity)

        assert velocities[-1] == 0.0
        assert robot.motion_state == "stopped"

        # Monotonic decrease
        for i in range(1, len(velocities)):
            assert velocities[i] <= velocities[i - 1]

    def test_sensors_detect_close_human(self):
        """Robot sensors detect human at 2m distance."""
        world = World(
            zone=Zone(zone_id="zone-c", width=50.0, height=30.0),
            robots=[Robot(robot_id="robot-1", zone_id="zone-c", x=10.0, y=10.0)],
            humans=[Human(human_id="human-1", zone_id="zone-c", x=12.0, y=10.0)],
            rng=random.Random(42),
            producer=None,
        )

        world.tick(0.1)
        robot = world.robots[0]

        assert robot.ultrasonic_distance is not None
        assert 1.5 <= robot.ultrasonic_distance <= 2.5

        assert robot.ble_rssi is not None
        assert robot.ble_rssi > -60


class TestScenario_VisibilityDegradation:
    """
    SCENARIO: Visibility conditions affect zone status.

    Demonstrates environmental condition toggles for
    simulating different warehouse scenarios.
    """

    def test_visibility_persists_across_ticks(self):
        """Visibility setting persists as simulation runs."""
        world = World(
            zone=Zone(zone_id="zone-c", width=50.0, height=30.0),
            robots=[Robot(robot_id="robot-1", zone_id="zone-c", x=10.0, y=10.0)],
            humans=[],
            rng=random.Random(42),
            producer=None,
        )

        world.zone.visibility = "poor"

        for _ in range(100):
            world.tick(0.1)

        state = world.get_state()
        assert state["zone"]["visibility"] == "poor"


class TestScenario_ScaleUpSimulation:
    """
    SCENARIO: Dynamically scale robots and humans.

    Demonstrates that simulation can grow to handle
    larger warehouse operations.
    """

    def test_scale_increases_congestion(self):
        """Scaling up increases zone congestion."""
        world = World(
            zone=Zone(zone_id="zone-c", width=50.0, height=30.0),
            robots=[
                Robot(robot_id="robot-1", zone_id="zone-c", x=10.0, y=10.0),
                Robot(robot_id="robot-2", zone_id="zone-c", x=40.0, y=20.0),
            ],
            humans=[
                Human(human_id="human-1", zone_id="zone-c", x=25.0, y=15.0),
            ],
            rng=random.Random(42),
            producer=None,
        )

        world.add_robots(8)
        world.add_humans(9)

        assert len(world.robots) == 10
        assert len(world.humans) == 10

        for _ in range(10):
            world.tick(0.1)

        state = world.get_state()
        assert state["zone"]["congestion_level"] > 0.1

    def test_new_entities_have_valid_state(self):
        """Newly added entities are properly initialized."""
        world = World(
            zone=Zone(zone_id="zone-c", width=50.0, height=30.0),
            robots=[],
            humans=[],
            rng=random.Random(42),
            producer=None,
        )

        world.add_robots(5)
        world.add_humans(5)

        for robot in world.robots:
            assert robot.robot_id.startswith("robot-")
            assert 0 <= robot.x <= 50.0
            assert 0 <= robot.y <= 30.0
            assert robot.target_x is not None


class TestScenario_MultiRobotCoordination:
    """
    SCENARIO: Multiple robots receive different commands.

    Demonstrates that each robot can be controlled independently.
    """

    def test_different_commands_per_robot(self):
        """Each robot responds to its own command."""
        world = World(
            zone=Zone(zone_id="zone-c", width=50.0, height=30.0),
            robots=[
                Robot(robot_id="robot-1", zone_id="zone-c", x=10.0, y=10.0),
                Robot(robot_id="robot-2", zone_id="zone-c", x=25.0, y=15.0),
                Robot(robot_id="robot-3", zone_id="zone-c", x=40.0, y=20.0),
            ],
            humans=[],
            rng=random.Random(42),
            producer=None,
        )

        # Set targets for all robots (start from rest)
        for robot in world.robots:
            robot.target_x = robot.x + 20.0
            robot.target_y = robot.y
            # Don't set velocity - let them accelerate from 0

        # Apply different commands
        world.apply_decision("robot-1", "STOP")     # Will stay stopped
        world.apply_decision("robot-2", "SLOW")     # Will accelerate to max 0.5
        world.apply_decision("robot-3", "CONTINUE") # Will accelerate to max 2.0

        # Run simulation
        for _ in range(30):
            world.tick(0.1)

        states = {r.robot_id: r for r in world.robots}

        # STOP: stays at 0 (can't accelerate)
        assert states["robot-1"].velocity == 0.0
        # SLOW: limited to 0.5 m/s max
        assert states["robot-2"].velocity <= 0.5
        assert states["robot-2"].velocity > 0  # But should be moving
        # CONTINUE: can reach full speed (2.0 m/s)
        assert states["robot-3"].velocity > 0.5
