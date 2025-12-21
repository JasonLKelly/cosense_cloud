"""
Unit tests for World engine.

These tests have NO external dependencies - no Kafka, no network.
Run with: pytest tests/unit/test_world.py -v
"""

import random
import pytest

from src.entities import Robot, Human, Zone
from src.world import World, distance, rssi_from_distance


class TestUtilityFunctions:
    """Tests for world.py utility functions."""

    def test_distance_same_point(self):
        """Distance between same point is zero."""
        assert distance(5.0, 5.0, 5.0, 5.0) == 0.0

    def test_distance_horizontal(self):
        """Distance for horizontal separation."""
        assert distance(0.0, 0.0, 3.0, 0.0) == 3.0

    def test_distance_vertical(self):
        """Distance for vertical separation."""
        assert distance(0.0, 0.0, 0.0, 4.0) == 4.0

    def test_distance_diagonal_345(self):
        """Distance for 3-4-5 triangle."""
        assert distance(0.0, 0.0, 3.0, 4.0) == 5.0

    def test_rssi_at_1m_approx_minus_40(self):
        """RSSI is approximately -40 dBm at 1 meter."""
        rng = random.Random(42)
        rssi = rssi_from_distance(1.0, rng)
        assert -50 <= rssi <= -30

    def test_rssi_decreases_with_distance(self):
        """RSSI decreases as distance increases."""
        rng = random.Random(42)
        rssi_near = rssi_from_distance(1.0, rng)
        rssi_far = rssi_from_distance(10.0, rng)
        assert rssi_far < rssi_near


class TestWorldCreation:
    """Tests for World initialization."""

    def test_world_has_entities(self, world: World):
        """World fixture has expected entities."""
        assert len(world.robots) == 2
        assert len(world.humans) == 2
        assert world.zone is not None

    def test_world_starts_stopped(self, world: World):
        """World starts not running."""
        assert world.running is False
        assert world.sim_time == 0.0

    def test_world_no_producer_in_unit_tests(self, world: World):
        """Unit test world has no Kafka producer."""
        assert world.producer is None


class TestWorldTick:
    """Tests for World tick behavior."""

    def test_tick_advances_time(self, world: World):
        """Tick increases simulation time."""
        initial_time = world.sim_time
        world.tick(0.1)
        assert world.sim_time == initial_time + 0.1

    def test_tick_updates_entities(self, world: World):
        """Tick updates entity positions."""
        for robot in world.robots:
            robot.target_x = robot.x + 10.0
            robot.target_y = robot.y

        for _ in range(10):
            world.tick(0.1)

        moving_robots = [r for r in world.robots if r.velocity > 0]
        assert len(moving_robots) > 0

    def test_tick_updates_zone_congestion(self, world: World):
        """Tick updates zone congestion."""
        world.tick(0.1)

        assert world.zone.robot_count == len(world.robots)
        assert world.zone.human_count == len(world.humans)


class TestWorldSensors:
    """Tests for sensor simulation."""

    def test_ultrasonic_detects_nearby_human(self, world_close_proximity: World):
        """Ultrasonic sensor detects human within 10m."""
        world = world_close_proximity
        world.tick(0.1)

        robot = world.robots[0]
        assert robot.ultrasonic_distance is not None
        assert 1.5 <= robot.ultrasonic_distance <= 2.5  # ~2m with noise

    def test_ble_detects_nearby_human(self, world_close_proximity: World):
        """BLE RSSI detects human within 15m."""
        world = world_close_proximity
        world.tick(0.1)

        robot = world.robots[0]
        assert robot.ble_rssi is not None
        assert -60 <= robot.ble_rssi <= -35  # ~2m

    def test_sensors_none_when_human_far(self):
        """Sensors return None when human is out of range."""
        world = World(
            zone=Zone(zone_id="test-zone", width=100.0, height=100.0),
            robots=[Robot(robot_id="robot-1", zone_id="test-zone", x=10.0, y=10.0)],
            humans=[Human(human_id="human-1", zone_id="test-zone", x=90.0, y=90.0)],
            rng=random.Random(42),
            producer=None,
        )
        world.tick(0.1)

        robot = world.robots[0]
        assert robot.ultrasonic_distance is None
        assert robot.ble_rssi is None

    @pytest.mark.parametrize("dist,expect_ultrasonic,expect_ble", [
        (2.0, True, True),
        (8.0, True, True),
        (12.0, False, True),
        (18.0, False, False),
    ])
    def test_sensor_detection_ranges(self, dist: float, expect_ultrasonic: bool, expect_ble: bool):
        """Test sensor detection at various distances."""
        world = World(
            zone=Zone(zone_id="test-zone", width=100.0, height=100.0),
            robots=[Robot(robot_id="robot-1", zone_id="test-zone", x=10.0, y=10.0)],
            humans=[Human(human_id="human-1", zone_id="test-zone", x=10.0 + dist, y=10.0)],
            rng=random.Random(42),
            producer=None,
        )
        world.tick(0.1)

        robot = world.robots[0]

        if expect_ultrasonic:
            assert robot.ultrasonic_distance is not None
        else:
            assert robot.ultrasonic_distance is None

        if expect_ble:
            assert robot.ble_rssi is not None
        else:
            assert robot.ble_rssi is None


class TestWorldScaling:
    """Tests for adding entities dynamically."""

    def test_add_robots(self, world: World):
        """Can add robots to simulation."""
        initial_count = len(world.robots)
        world.add_robots(3)

        assert len(world.robots) == initial_count + 3

        for robot in world.robots[initial_count:]:
            assert 0 <= robot.x <= world.zone.width
            assert 0 <= robot.y <= world.zone.height
            assert robot.target_x is not None

    def test_add_humans(self, world: World):
        """Can add humans to simulation."""
        initial_count = len(world.humans)
        world.add_humans(5)

        assert len(world.humans) == initial_count + 5


class TestWorldDecisions:
    """Tests for applying coordination decisions."""

    def test_apply_stop_decision(self, world: World):
        """Apply STOP decision to robot."""
        world.apply_decision("robot-1", "STOP")

        robot = next(r for r in world.robots if r.robot_id == "robot-1")
        assert robot.commanded_action == "STOP"

    def test_apply_slow_decision(self, world: World):
        """Apply SLOW decision to robot."""
        world.apply_decision("robot-2", "SLOW")

        robot = next(r for r in world.robots if r.robot_id == "robot-2")
        assert robot.commanded_action == "SLOW"

    def test_apply_decision_unknown_robot_is_noop(self, world: World):
        """Applying decision to unknown robot is no-op."""
        world.apply_decision("unknown-robot", "STOP")

        for robot in world.robots:
            assert robot.commanded_action == "CONTINUE"


class TestWorldState:
    """Tests for state serialization."""

    def test_get_state_structure(self, world: World):
        """get_state returns expected structure."""
        world.tick(0.1)
        state = world.get_state()

        assert "sim_time" in state
        assert "running" in state
        assert "zone" in state
        assert "robots" in state
        assert "humans" in state

    def test_get_state_zone_data(self, world: World):
        """get_state includes zone information."""
        world.zone.visibility = "degraded"
        world.zone.connectivity = "offline"
        world.tick(0.1)

        state = world.get_state()
        zone = state["zone"]

        assert zone["zone_id"] == "test-zone"
        assert zone["visibility"] == "degraded"
        assert zone["connectivity"] == "offline"

    def test_get_state_robot_fields(self, world: World):
        """get_state includes all robot fields."""
        world.tick(0.1)
        state = world.get_state()

        robot_state = state["robots"][0]
        required_fields = ["robot_id", "x", "y", "velocity", "heading", "motion_state", "commanded_action"]
        for field in required_fields:
            assert field in robot_state

    def test_get_state_human_fields(self, world: World):
        """get_state includes all human fields."""
        world.tick(0.1)
        state = world.get_state()

        human_state = state["humans"][0]
        required_fields = ["human_id", "x", "y", "velocity"]
        for field in required_fields:
            assert field in human_state
