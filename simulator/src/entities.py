"""Simulated entities: robots and humans."""

import math
import random
from dataclasses import dataclass, field
from typing import Literal


@dataclass
class Robot:
    """A simulated robot in the warehouse."""

    robot_id: str
    zone_id: str
    x: float
    y: float
    velocity: float = 0.0
    heading: float = 0.0  # degrees
    motion_state: Literal["moving", "stopped", "slowing"] = "stopped"

    # Path following
    path: list[tuple[float, float]] = field(default_factory=list)
    path_index: int = 0
    destination_waypoint: str | None = None

    # Legacy target support (for backward compatibility)
    target_x: float | None = None
    target_y: float | None = None

    # Sensor readings (computed each tick)
    ultrasonic_distance: float | None = None
    ble_rssi: float | None = None

    # Commanded state (from coordination decisions)
    commanded_action: Literal["CONTINUE", "SLOW", "STOP", "REROUTE"] = "CONTINUE"

    # Manual override - when True, stream-processor decisions are ignored
    manual_override: bool = False

    def set_path(self, path: list[tuple[float, float]], destination: str | None = None):
        """Set a new path for the robot to follow."""
        self.path = path
        self.path_index = 0
        self.destination_waypoint = destination
        if path:
            self.target_x, self.target_y = path[0]

    def pick_new_target(self, world_width: float, world_height: float, rng: random.Random):
        """Pick a new random target location (legacy method)."""
        margin = 2.0
        self.target_x = rng.uniform(margin, world_width - margin)
        self.target_y = rng.uniform(margin, world_height - margin)
        self.path = []
        self.path_index = 0

    def update(self, dt: float, world_width: float, world_height: float, rng: random.Random):
        """Update position based on current state and target/path."""
        max_speed = 2.0  # m/s
        acceleration = 1.0  # m/s^2

        # Handle commanded actions
        if self.commanded_action == "STOP":
            self.velocity = max(0, self.velocity - acceleration * 2 * dt)
            self.motion_state = "stopped" if self.velocity == 0 else "slowing"
            return
        elif self.commanded_action == "SLOW":
            max_speed = 0.5

        # Get current target
        target_x = self.target_x
        target_y = self.target_y

        if target_x is None or target_y is None:
            self.velocity = 0.0
            self.motion_state = "stopped"
            return

        # Calculate direction to target
        dx = target_x - self.x
        dy = target_y - self.y
        distance_to_target = math.sqrt(dx * dx + dy * dy)

        # Reached current waypoint?
        if distance_to_target < 0.5:
            if self.path and self.path_index < len(self.path) - 1:
                # Move to next waypoint in path
                self.path_index += 1
                self.target_x, self.target_y = self.path[self.path_index]
            else:
                # Reached end of path - signal that we need a new destination
                self.path = []
                self.path_index = 0
                self.target_x = None
                self.target_y = None
                self.destination_waypoint = None
            return

        # Update heading
        self.heading = math.degrees(math.atan2(dy, dx)) % 360

        # Accelerate or maintain speed
        if self.velocity < max_speed:
            self.velocity = min(max_speed, self.velocity + acceleration * dt)

        self.motion_state = "moving" if self.velocity > 0.1 else "stopped"

        # Move
        move_dist = self.velocity * dt
        self.x += (dx / distance_to_target) * move_dist
        self.y += (dy / distance_to_target) * move_dist

        # Clamp to world bounds
        self.x = max(0, min(world_width, self.x))
        self.y = max(0, min(world_height, self.y))


@dataclass
class Human:
    """A simulated human worker in the warehouse."""

    human_id: str
    zone_id: str
    x: float
    y: float
    velocity: float = 0.0
    heading: float | None = None

    # Movement pattern
    target_x: float | None = None
    target_y: float | None = None
    idle_until: float = 0.0  # timestamp when idle period ends

    # Workstation assignment (for realistic movement)
    assigned_zone: str | None = None
    home_x: float | None = None
    home_y: float | None = None

    def set_home(self, x: float, y: float, zone: str | None = None):
        """Set the human's home position (workstation)."""
        self.home_x = x
        self.home_y = y
        self.assigned_zone = zone

    def pick_new_target(self, world_width: float, world_height: float, rng: random.Random):
        """Pick a new target location."""
        margin = 2.0

        # If has a home position, usually stay near it
        if self.home_x is not None and self.home_y is not None:
            if rng.random() < 0.7:  # 70% chance to stay near home
                self.target_x = self.home_x + rng.gauss(0, 3)
                self.target_y = self.home_y + rng.gauss(0, 3)
                # Clamp
                self.target_x = max(margin, min(world_width - margin, self.target_x))
                self.target_y = max(margin, min(world_height - margin, self.target_y))
                return

        # Otherwise random location
        self.target_x = rng.uniform(margin, world_width - margin)
        self.target_y = rng.uniform(margin, world_height - margin)

    def update(self, dt: float, sim_time: float, world_width: float, world_height: float, rng: random.Random):
        """Update position - humans move more erratically than robots."""
        max_speed = 1.5  # m/s (walking speed)

        # Sometimes humans stop and idle
        if sim_time < self.idle_until:
            self.velocity = 0.0
            return

        # Random chance to start idling
        if rng.random() < 0.002:  # ~0.2% chance per tick
            self.idle_until = sim_time + rng.uniform(2.0, 8.0)
            self.velocity = 0.0
            return

        # Pick new target if needed
        if self.target_x is None or self.target_y is None:
            self.pick_new_target(world_width, world_height, rng)

        # Calculate direction to target
        dx = self.target_x - self.x
        dy = self.target_y - self.y
        distance_to_target = math.sqrt(dx * dx + dy * dy)

        # Reached target?
        if distance_to_target < 0.5:
            self.pick_new_target(world_width, world_height, rng)
            # Maybe idle at destination
            if rng.random() < 0.3:
                self.idle_until = sim_time + rng.uniform(1.0, 5.0)
            return

        # Update heading and velocity (with some randomness)
        self.heading = math.degrees(math.atan2(dy, dx)) % 360
        target_velocity = rng.uniform(0.5, max_speed)
        self.velocity = self.velocity * 0.9 + target_velocity * 0.1  # smooth

        # Move
        move_dist = self.velocity * dt
        self.x += (dx / distance_to_target) * move_dist
        self.y += (dy / distance_to_target) * move_dist

        # Clamp to world bounds
        self.x = max(0, min(world_width, self.x))
        self.y = max(0, min(world_height, self.y))


@dataclass
class Zone:
    """A warehouse zone with environmental conditions."""

    zone_id: str
    width: float
    height: float

    # Conditions (can be toggled via scenario API)
    visibility: Literal["normal", "degraded", "poor"] = "normal"
    connectivity: Literal["normal", "degraded", "offline"] = "normal"

    # Computed each tick
    robot_count: int = 0
    human_count: int = 0
    congestion_level: float = 0.0

    def update_congestion(self, robot_count: int, human_count: int):
        """Update congestion based on entity counts."""
        self.robot_count = robot_count
        self.human_count = human_count
        # Simple formula: congestion increases with density
        area = self.width * self.height
        entity_density = (robot_count + human_count) / area
        # Normalize: 0.01 entities/m² = 0.5 congestion
        self.congestion_level = min(1.0, entity_density / 0.02)
