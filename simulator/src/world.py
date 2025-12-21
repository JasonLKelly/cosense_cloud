"""World engine - manages simulation state and emits telemetry."""

import json
import math
import random
import time
from dataclasses import dataclass

from confluent_kafka import Producer

from .config import settings
from .entities import Robot, Human, Zone


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

    zone: Zone
    robots: list[Robot]
    humans: list[Human]
    rng: random.Random
    producer: Producer | None = None

    sim_time: float = 0.0  # Simulation time in seconds
    running: bool = False

    @classmethod
    def create(cls, producer: Producer | None = None) -> "World":
        """Create a new world with initial entities."""
        seed = settings.seed if settings.seed != 0 else int(time.time() * 1000)
        rng = random.Random(seed)

        zone = Zone(
            zone_id=settings.zone_id,
            width=settings.world_width,
            height=settings.world_height,
        )

        # Create robots
        robots = []
        for i in range(settings.robot_count):
            robot = Robot(
                robot_id=f"robot-{i + 1}",
                zone_id=zone.zone_id,
                x=rng.uniform(5, zone.width - 5),
                y=rng.uniform(5, zone.height - 5),
            )
            robot.pick_new_target(zone.width, zone.height, rng)
            robots.append(robot)

        # Create humans
        humans = []
        for i in range(settings.human_count):
            human = Human(
                human_id=f"human-{i + 1}",
                zone_id=zone.zone_id,
                x=rng.uniform(5, zone.width - 5),
                y=rng.uniform(5, zone.height - 5),
            )
            human.pick_new_target(zone.width, zone.height, rng)
            humans.append(human)

        return cls(
            zone=zone,
            robots=robots,
            humans=humans,
            rng=rng,
            producer=producer,
        )

    def add_robots(self, count: int):
        """Add more robots to the simulation."""
        start_id = len(self.robots) + 1
        for i in range(count):
            robot = Robot(
                robot_id=f"robot-{start_id + i}",
                zone_id=self.zone.zone_id,
                x=self.rng.uniform(5, self.zone.width - 5),
                y=self.rng.uniform(5, self.zone.height - 5),
            )
            robot.pick_new_target(self.zone.width, self.zone.height, self.rng)
            self.robots.append(robot)

    def add_humans(self, count: int):
        """Add more humans to the simulation."""
        start_id = len(self.humans) + 1
        for i in range(count):
            human = Human(
                human_id=f"human-{start_id + i}",
                zone_id=self.zone.zone_id,
                x=self.rng.uniform(5, self.zone.width - 5),
                y=self.rng.uniform(5, self.zone.height - 5),
            )
            human.pick_new_target(self.zone.width, self.zone.height, self.rng)
            self.humans.append(human)

    def tick(self, dt: float):
        """Advance simulation by dt seconds."""
        self.sim_time += dt

        # Update all entities
        for robot in self.robots:
            robot.update(dt, self.zone.width, self.zone.height, self.rng)

        for human in self.humans:
            human.update(dt, self.sim_time, self.zone.width, self.zone.height, self.rng)

        # Update robot sensors
        for robot in self.robots:
            self._update_robot_sensors(robot)

        # Update zone
        self.zone.update_congestion(len(self.robots), len(self.humans))

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
                "zone_id": robot.zone_id,
                "x": round(robot.x, 2),
                "y": round(robot.y, 2),
                "velocity": round(robot.velocity, 2),
                "heading": round(robot.heading, 1),
                "motion_state": robot.motion_state,
                "ultrasonic_distance": robot.ultrasonic_distance,
                "ble_rssi": robot.ble_rssi,
            }
            self.producer.produce(
                "robot.telemetry",
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
                "zone_id": human.zone_id,
                "x": round(human.x + pos_noise, 2),
                "y": round(human.y + pos_noise, 2),
                "velocity": round(human.velocity, 2),
                "heading": round(human.heading, 1) if human.heading else None,
                "position_confidence": round(confidence, 2),
            }
            self.producer.produce(
                "human.telemetry",
                key=human.human_id,
                value=json.dumps(event),
            )

        # Zone context (less frequent, but emit each tick for simplicity)
        zone_event = {
            "zone_id": self.zone.zone_id,
            "timestamp": timestamp,
            "visibility": self.zone.visibility,
            "congestion_level": round(self.zone.congestion_level, 2),
            "robot_count": self.zone.robot_count,
            "human_count": self.zone.human_count,
            "connectivity": self.zone.connectivity,
        }
        self.producer.produce(
            "zone.context",
            key=self.zone.zone_id,
            value=json.dumps(zone_event),
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
            "zone": {
                "zone_id": self.zone.zone_id,
                "width": self.zone.width,
                "height": self.zone.height,
                "visibility": self.zone.visibility,
                "connectivity": self.zone.connectivity,
                "congestion_level": round(self.zone.congestion_level, 2),
            },
            "robots": [
                {
                    "robot_id": r.robot_id,
                    "x": round(r.x, 2),
                    "y": round(r.y, 2),
                    "velocity": round(r.velocity, 2),
                    "heading": round(r.heading, 1),
                    "motion_state": r.motion_state,
                    "commanded_action": r.commanded_action,
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
