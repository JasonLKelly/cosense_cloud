"""World engine - manages simulation state and emits telemetry."""

import json
import math
import random
import time
from dataclasses import dataclass, field
from pathlib import Path

from confluent_kafka import Producer

from .config import settings
from .entities import Robot, Human
from .pathfinding import Pathfinder, create_pathfinder_from_map


def distance(x1: float, y1: float, x2: float, y2: float) -> float:
    """Euclidean distance between two points."""
    return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)


def rssi_from_distance(dist: float, rng: random.Random) -> float:
    """Convert distance to simulated BLE RSSI (with noise)."""
    # RSSI model: -40 dBm at 1m, decreases ~20 dBm per decade
    if dist < 0.1:
        dist = 0.1
    rssi = -40 - 20 * math.log10(dist)
    # Add noise (±5 dBm)
    rssi += rng.gauss(0, 2.5)
    return round(rssi, 1)


@dataclass
class World:
    """The simulation world."""

    width: float
    height: float
    robots: list[Robot]
    humans: list[Human]
    rng: random.Random
    producer: Producer | None = None

    # Map data
    map_data: dict = field(default_factory=dict)
    waypoints: list[dict] = field(default_factory=list)
    pathfinder: Pathfinder | None = None

    sim_time: float = 0.0  # Simulation time in seconds
    running: bool = False

    # Environmental conditions (can be toggled via scenario API)
    visibility: str = "normal"  # normal, degraded, poor
    connectivity: str = "normal"  # normal, degraded, offline
    congestion_level: float = 0.0

    @classmethod
    def create(
        cls,
        producer: Producer | None = None,
        map_id: str = "zone-c",
        robot_count: int | None = None,
        human_count: int | None = None,
    ) -> "World":
        """Create a new world with initial entities."""
        seed = settings.seed if settings.seed != 0 else int(time.time() * 1000)
        rng = random.Random(seed)

        # Use provided counts or fall back to settings
        num_robots = robot_count if robot_count is not None else settings.robot_count
        num_humans = human_count if human_count is not None else settings.human_count

        # Load map
        map_data = cls._load_map(map_id)
        waypoints = map_data.get("waypoints", [])

        width = map_data.get("width", settings.world_width)
        height = map_data.get("height", settings.world_height)

        # Create pathfinder from map
        pathfinder = create_pathfinder_from_map(map_data) if map_data else None

        # Get spawn locations - use waypoints that start with "charge" for robots
        robot_spawn_waypoints = [
            wp for wp in waypoints
            if wp["id"].startswith("charge")
        ]
        # Use waypoints that start with "pack" for humans
        human_spawn_waypoints = [
            wp for wp in waypoints
            if wp["id"].startswith("pack")
        ]

        # Create robots at charging stations
        robots = []
        for i in range(num_robots):
            if robot_spawn_waypoints:
                spawn = rng.choice(robot_spawn_waypoints)
                x, y = spawn["x"], spawn["y"]
            else:
                x = rng.uniform(5, width - 5)
                y = rng.uniform(5, height - 5)

            robot = Robot(
                robot_id=f"robot-{i + 1}",
                x=x + rng.uniform(-1, 1),
                y=y + rng.uniform(-1, 1),
            )
            robots.append(robot)

        # Create humans at workstations
        humans = []
        for i in range(num_humans):
            if human_spawn_waypoints:
                spawn = rng.choice(human_spawn_waypoints)
                x, y = spawn["x"], spawn["y"]
            else:
                x = rng.uniform(5, width - 5)
                y = rng.uniform(5, height - 5)

            human = Human(
                human_id=f"human-{i + 1}",
                x=x + rng.uniform(-1, 1),
                y=y + rng.uniform(-1, 1),
            )
            human.set_home(x, y)
            humans.append(human)

        world = cls(
            width=width,
            height=height,
            robots=robots,
            humans=humans,
            rng=rng,
            producer=producer,
            map_data=map_data,
            waypoints=waypoints,
            pathfinder=pathfinder,
        )

        # Assign initial destinations to robots
        for robot in robots:
            world._assign_random_destination(robot)

        return world

    @staticmethod
    def _load_map(map_id: str) -> dict:
        """Load map from JSON file."""
        # Try multiple locations
        possible_paths = [
            Path("/app/maps") / f"{map_id}.json",  # Docker mount
            Path(__file__).parent.parent.parent / "maps" / f"{map_id}.json",  # Local dev
        ]

        for map_file in possible_paths:
            if map_file.exists():
                with open(map_file) as f:
                    return json.load(f)

        # Fall back to empty map (use default settings)
        return {}

    def _assign_random_destination(self, robot: Robot):
        """Assign a random waypoint destination to a robot."""
        if not self.waypoints or not self.pathfinder:
            # Fall back to random target
            robot.pick_new_target(self.width, self.height, self.rng)
            return

        # Pick a random waypoint (excluding charging stations for destinations)
        valid_waypoints = [
            wp for wp in self.waypoints
            if not wp["id"].startswith("charge")
        ]

        if not valid_waypoints:
            valid_waypoints = self.waypoints

        destination = self.rng.choice(valid_waypoints)

        # Find path using A*
        path = self.pathfinder.find_path(
            robot.x, robot.y,
            destination["x"], destination["y"]
        )

        if path:
            robot.set_path(path, destination["id"])
        else:
            # No path found, fall back to random movement
            robot.pick_new_target(self.width, self.height, self.rng)

    def add_robots(self, count: int):
        """Add more robots to the simulation."""
        start_id = len(self.robots) + 1

        # Get spawn waypoints
        robot_spawn_waypoints = [
            wp for wp in self.waypoints
            if wp["id"].startswith("charge")
        ]

        for i in range(count):
            if robot_spawn_waypoints:
                spawn = self.rng.choice(robot_spawn_waypoints)
                x, y = spawn["x"], spawn["y"]
            else:
                x = self.rng.uniform(5, self.width - 5)
                y = self.rng.uniform(5, self.height - 5)

            robot = Robot(
                robot_id=f"robot-{start_id + i}",
                x=x + self.rng.uniform(-1, 1),
                y=y + self.rng.uniform(-1, 1),
            )
            self._assign_random_destination(robot)
            self.robots.append(robot)

    def add_humans(self, count: int):
        """Add more humans to the simulation."""
        start_id = len(self.humans) + 1

        human_spawn_waypoints = [
            wp for wp in self.waypoints
            if wp["id"].startswith("pack")
        ]

        for i in range(count):
            if human_spawn_waypoints:
                spawn = self.rng.choice(human_spawn_waypoints)
                x, y = spawn["x"], spawn["y"]
            else:
                x = self.rng.uniform(5, self.width - 5)
                y = self.rng.uniform(5, self.height - 5)

            human = Human(
                human_id=f"human-{start_id + i}",
                x=x + self.rng.uniform(-1, 1),
                y=y + self.rng.uniform(-1, 1),
            )
            human.set_home(x, y)
            human.pick_new_target(self.width, self.height, self.rng)
            self.humans.append(human)

    def tick(self, dt: float):
        """Advance simulation by dt seconds."""
        self.sim_time += dt

        # Update dynamic obstacles for pathfinder (other robots)
        if self.pathfinder:
            dynamic_obs = set()
            for robot in self.robots:
                gx, gy = self.pathfinder.world_to_grid(robot.x, robot.y)
                dynamic_obs.add((gx, gy))
            self.pathfinder.set_dynamic_obstacles(dynamic_obs)

        # Update all entities
        for robot in self.robots:
            robot.update(
                dt,
                self.width,
                self.height,
                self.rng,
                self.sim_time,
                other_robots=self.robots,
                robot_buffer_distance=settings.robot_buffer_distance,
            )
            # Assign new destination if needed (only if not paused and not stopped)
            if robot.target_x is None and robot.commanded_action != "STOP" and self.sim_time >= robot.idle_until:
                self._assign_random_destination(robot)

        for human in self.humans:
            human.update(dt, self.sim_time, self.width, self.height, self.rng)

        # Update robot sensors
        for robot in self.robots:
            self._update_robot_sensors(robot)

        # Update congestion level
        self._update_congestion()

    def _update_congestion(self):
        """Update congestion based on entity counts."""
        # Simple formula: congestion increases with density
        area = self.width * self.height
        entity_density = (len(self.robots) + len(self.humans)) / area
        # Normalize: 0.01 entities/m² = 0.5 congestion
        self.congestion_level = min(1.0, entity_density / 0.02)

    def _update_robot_sensors(self, robot: Robot):
        """Update simulated sensor readings for a robot."""
        # Find nearest human
        min_dist = float("inf")
        for human in self.humans:
            dist = distance(robot.x, robot.y, human.x, human.y)
            if dist < min_dist:
                min_dist = dist

        # Ultrasonic: detect obstacles (including humans) with noise
        if min_dist < 10.0:  # 10m range
            noise = self.rng.gauss(0, 0.1)  # ±10cm noise
            robot.ultrasonic_distance = round(max(0.1, min_dist + noise), 2)
        else:
            robot.ultrasonic_distance = None

        # BLE RSSI: detect humans via beacon
        if min_dist < 15.0:  # 15m range
            robot.ble_rssi = rssi_from_distance(min_dist, self.rng)
        else:
            robot.ble_rssi = None

    def emit_telemetry(self):
        """Emit all telemetry events to Kafka."""
        if not self.producer:
            return

        timestamp = int(time.time() * 1000)

        # Robot telemetry
        for robot in self.robots:
            event = {
                "robot_id": robot.robot_id,
                "timestamp": timestamp,
                "x": round(robot.x, 2),
                "y": round(robot.y, 2),
                "velocity": round(robot.velocity, 2),
                "heading": round(robot.heading, 1),
                "motion_state": robot.motion_state,
                "ultrasonic_distance": robot.ultrasonic_distance,
                "ble_rssi": robot.ble_rssi,
                "destination": robot.destination_waypoint,
            }
            self.producer.produce(
                settings.topic("robot.telemetry"),
                key=robot.robot_id,
                value=json.dumps(event),
            )

        # Human telemetry
        for human in self.humans:
            # Humans have less precise positioning
            pos_noise = self.rng.gauss(0, 0.3)
            confidence = max(0.5, 1.0 - abs(pos_noise) / 2)

            event = {
                "human_id": human.human_id,
                "timestamp": timestamp,
                "x": round(human.x + pos_noise, 2),
                "y": round(human.y + pos_noise, 2),
                "velocity": round(human.velocity, 2),
                "heading": round(human.heading, 1) if human.heading else None,
                "position_confidence": round(confidence, 2),
            }
            self.producer.produce(
                settings.topic("human.telemetry"),
                key=human.human_id,
                value=json.dumps(event),
            )

        # Flush to ensure delivery
        self.producer.flush(timeout=0.1)

    def apply_decision(self, robot_id: str, action: str):
        """Apply a coordination decision to a robot."""
        for robot in self.robots:
            if robot.robot_id == robot_id:
                robot.commanded_action = action
                break

    def get_state(self) -> dict:
        """Get current world state for API responses."""
        return {
            "sim_time": round(self.sim_time, 2),
            "running": self.running,
            "map_id": self.map_data.get("id", "default"),
            "width": self.width,
            "height": self.height,
            "visibility": self.visibility,
            "connectivity": self.connectivity,
            "congestion_level": round(self.congestion_level, 2),
            "robot_count": len(self.robots),
            "human_count": len(self.humans),
            "robots": [
                {
                    "robot_id": r.robot_id,
                    "x": round(r.x, 2),
                    "y": round(r.y, 2),
                    "velocity": round(r.velocity, 2),
                    "heading": round(r.heading, 1),
                    "motion_state": r.motion_state,
                    "commanded_action": r.commanded_action,
                    "destination": r.destination_waypoint,
                    "manual_override": r.manual_override,
                }
                for r in self.robots
            ],
            "humans": [
                {
                    "human_id": h.human_id,
                    "x": round(h.x, 2),
                    "y": round(h.y, 2),
                    "velocity": round(h.velocity, 2),
                }
                for h in self.humans
            ],
        }
