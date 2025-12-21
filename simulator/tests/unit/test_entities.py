"""
Unit tests for Robot, Human, and Zone entities.

These tests have NO external dependencies - pure Python only.
Run with: pytest tests/unit/test_entities.py -v
"""

import random
import pytest
from src.entities import Robot, Human, Zone


class TestRobot:
    """Tests for Robot entity behavior."""

    def test_robot_initial_state(self, robot: Robot):
        """Robot starts stopped with no velocity."""
        assert robot.velocity == 0.0
        assert robot.motion_state == "stopped"
        assert robot.commanded_action == "CONTINUE"

    def test_robot_pick_new_target(self, robot: Robot, zone: Zone, rng: random.Random):
        """Robot picks target within zone bounds."""
        robot.pick_new_target(zone.width, zone.height, rng)

        assert robot.target_x is not None
        assert robot.target_y is not None
        assert 2.0 <= robot.target_x <= zone.width - 2.0
        assert 2.0 <= robot.target_y <= zone.height - 2.0

    def test_robot_moves_toward_target(self, robot: Robot, zone: Zone, rng: random.Random):
        """Robot accelerates and moves toward its target."""
        robot.target_x = robot.x + 20.0
        robot.target_y = robot.y

        initial_x = robot.x

        for _ in range(10):
            robot.update(dt=0.1, world_width=zone.width, world_height=zone.height, rng=rng)

        assert robot.x > initial_x, "Robot should move toward target"
        assert robot.velocity > 0, "Robot should have positive velocity"
        assert robot.motion_state == "moving"

    def test_robot_stop_command(self, robot: Robot, zone: Zone, rng: random.Random):
        """Robot stops when commanded STOP."""
        robot.target_x = robot.x + 20.0
        robot.target_y = robot.y
        robot.velocity = 2.0
        robot.motion_state = "moving"

        robot.commanded_action = "STOP"

        for _ in range(20):
            robot.update(dt=0.1, world_width=zone.width, world_height=zone.height, rng=rng)
            if robot.velocity == 0:
                break

        assert robot.velocity == 0.0
        assert robot.motion_state == "stopped"

    def test_robot_slow_command(self, robot: Robot, zone: Zone, rng: random.Random):
        """Robot limits speed when commanded SLOW."""
        robot.target_x = robot.x + 20.0
        robot.target_y = robot.y
        robot.commanded_action = "SLOW"

        for _ in range(50):
            robot.update(dt=0.1, world_width=zone.width, world_height=zone.height, rng=rng)

        assert robot.velocity <= 0.5, f"SLOW should limit velocity to 0.5, got {robot.velocity}"

    def test_robot_continue_allows_full_speed(self, robot: Robot, zone: Zone, rng: random.Random):
        """Robot reaches full speed with CONTINUE command."""
        robot.target_x = robot.x + 20.0
        robot.target_y = robot.y
        robot.commanded_action = "CONTINUE"

        for _ in range(50):
            robot.update(dt=0.1, world_width=zone.width, world_height=zone.height, rng=rng)

        assert robot.velocity > 0.5, f"CONTINUE should allow velocity > 0.5, got {robot.velocity}"

    def test_robot_stays_in_bounds(self, zone: Zone, rng: random.Random):
        """Robot position is clamped to world bounds."""
        robot = Robot(
            robot_id="edge-robot",
            zone_id=zone.zone_id,
            x=zone.width - 0.1,
            y=zone.height - 0.1,
        )
        robot.target_x = zone.width + 100
        robot.target_y = zone.height + 100
        robot.velocity = 2.0

        for _ in range(20):
            robot.update(dt=0.1, world_width=zone.width, world_height=zone.height, rng=rng)

        assert 0 <= robot.x <= zone.width
        assert 0 <= robot.y <= zone.height


class TestHuman:
    """Tests for Human entity behavior."""

    def test_human_initial_state(self, human: Human):
        """Human starts with zero velocity."""
        assert human.velocity == 0.0
        assert human.idle_until == 0.0

    def test_human_picks_target_in_bounds(self, human: Human, zone: Zone, rng: random.Random):
        """Human picks target within zone bounds."""
        human.pick_new_target(zone.width, zone.height, rng)

        assert human.target_x is not None
        assert human.target_y is not None
        assert 2.0 <= human.target_x <= zone.width - 2.0
        assert 2.0 <= human.target_y <= zone.height - 2.0

    def test_human_moves_when_not_idle(self, human: Human, zone: Zone, rng: random.Random):
        """Human moves toward target when not idle."""
        human.target_x = human.x + 20.0
        human.target_y = human.y
        human.idle_until = 0.0

        initial_x = human.x

        for i in range(10):
            human.update(dt=0.1, sim_time=0.1 * i, world_width=zone.width, world_height=zone.height, rng=rng)

        assert human.x > initial_x or human.velocity > 0, "Human should move or have velocity"

    def test_human_stops_when_idle(self, human: Human, zone: Zone, rng: random.Random):
        """Human stops moving when in idle period."""
        human.target_x = human.x + 20.0
        human.target_y = human.y
        human.velocity = 1.0
        human.idle_until = 100.0  # Idle until sim_time=100

        human.update(dt=0.1, sim_time=1.0, world_width=zone.width, world_height=zone.height, rng=rng)

        assert human.velocity == 0.0

    def test_human_stays_in_bounds(self, zone: Zone, rng: random.Random):
        """Human position is clamped to world bounds."""
        human = Human(
            human_id="edge-human",
            zone_id=zone.zone_id,
            x=zone.width - 0.1,
            y=zone.height - 0.1,
        )
        human.target_x = zone.width + 100
        human.target_y = zone.height + 100
        human.velocity = 1.5
        human.idle_until = 0.0

        for i in range(20):
            human.update(dt=0.1, sim_time=i * 0.1, world_width=zone.width, world_height=zone.height, rng=rng)

        assert 0 <= human.x <= zone.width
        assert 0 <= human.y <= zone.height


class TestZone:
    """Tests for Zone entity behavior."""

    def test_zone_initial_state(self, zone: Zone):
        """Zone starts with normal conditions."""
        assert zone.visibility == "normal"
        assert zone.connectivity == "normal"
        assert zone.congestion_level == 0.0

    def test_zone_congestion_empty(self, zone: Zone):
        """Empty zone has zero congestion."""
        zone.update_congestion(robot_count=0, human_count=0)
        assert zone.congestion_level == 0.0

    def test_zone_congestion_moderate(self, zone: Zone):
        """Moderate entity count produces moderate congestion."""
        # 50x30 = 1500 m², 15 entities = 0.01/m² density = 0.5 congestion
        zone.update_congestion(robot_count=10, human_count=5)

        assert 0.4 <= zone.congestion_level <= 0.6
        assert zone.robot_count == 10
        assert zone.human_count == 5

    def test_zone_congestion_caps_at_one(self, zone: Zone):
        """High entity count caps congestion at 1.0."""
        zone.update_congestion(robot_count=50, human_count=50)
        assert zone.congestion_level == 1.0

    def test_zone_visibility_modes(self, zone: Zone):
        """Zone visibility can be changed."""
        zone.visibility = "degraded"
        assert zone.visibility == "degraded"

        zone.visibility = "poor"
        assert zone.visibility == "poor"

    def test_zone_connectivity_modes(self, zone: Zone):
        """Zone connectivity can be changed."""
        zone.connectivity = "degraded"
        assert zone.connectivity == "degraded"

        zone.connectivity = "offline"
        assert zone.connectivity == "offline"
