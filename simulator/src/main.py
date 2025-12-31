"""FastAPI application for the simulator."""

import asyncio
from contextlib import asynccontextmanager
from typing import Literal

from confluent_kafka import Producer
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .config import settings
from .world import World


# Global world instance
world: World | None = None
simulation_task: asyncio.Task | None = None


def create_producer() -> Producer:
    """Create Kafka producer."""
    config = settings.get_kafka_config()
    config["client.id"] = "cosense-simulator"
    return Producer(config)


async def simulation_loop():
    """Main simulation loop."""
    global world
    dt = 1.0 / settings.tick_rate_hz

    while world and world.running:
        world.tick(dt)
        world.emit_telemetry()
        await asyncio.sleep(dt)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - initialize world on startup."""
    global world
    try:
        producer = create_producer()
        world = World.create(producer=producer)
        print(f"Simulator initialized: {len(world.robots)} robots, {len(world.humans)} humans")
    except Exception as e:
        print(f"Warning: Could not connect to Kafka: {e}")
        world = World.create(producer=None)
        print("Running without Kafka (dry run mode)")

    yield

    # Cleanup
    if world and world.running:
        world.running = False
    if world and world.producer:
        world.producer.flush()


app = FastAPI(
    title="CoSense Simulator",
    description="Headless warehouse simulation for CoSense Cloud",
    version="0.1.0",
    lifespan=lifespan,
)


# Request/Response models
class ScenarioToggle(BaseModel):
    visibility: Literal["normal", "degraded", "poor"] | None = None
    connectivity: Literal["normal", "degraded", "offline"] | None = None


class ScaleRequest(BaseModel):
    robots: int | None = None
    humans: int | None = None


class DecisionCommand(BaseModel):
    robot_id: str
    action: Literal["CONTINUE", "SLOW", "STOP", "REROUTE"]


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "running": world.running if world else False}


@app.get("/state")
async def get_state():
    """Get current simulation state."""
    if not world:
        raise HTTPException(status_code=503, detail="World not initialized")
    return world.get_state()


@app.post("/scenario/start")
async def start_scenario():
    """Start the simulation."""
    global world, simulation_task

    if not world:
        raise HTTPException(status_code=503, detail="World not initialized")

    if world.running:
        return {"status": "already_running"}

    world.running = True
    simulation_task = asyncio.create_task(simulation_loop())

    return {"status": "started", "tick_rate_hz": settings.tick_rate_hz}


@app.post("/scenario/stop")
async def stop_scenario():
    """Stop the simulation."""
    global world, simulation_task

    if not world:
        raise HTTPException(status_code=503, detail="World not initialized")

    world.running = False
    if simulation_task:
        await simulation_task
        simulation_task = None

    return {"status": "stopped", "sim_time": world.sim_time}


@app.post("/scenario/toggle")
async def toggle_scenario(toggle: ScenarioToggle):
    """Toggle scenario conditions (visibility, connectivity)."""
    if not world:
        raise HTTPException(status_code=503, detail="World not initialized")

    if toggle.visibility:
        world.visibility = toggle.visibility
    if toggle.connectivity:
        world.connectivity = toggle.connectivity

    return {
        "visibility": world.visibility,
        "connectivity": world.connectivity,
    }


@app.post("/scenario/scale")
async def scale_scenario(scale: ScaleRequest):
    """Add more robots or humans to the simulation."""
    if not world:
        raise HTTPException(status_code=503, detail="World not initialized")

    if scale.robots and scale.robots > 0:
        world.add_robots(scale.robots)
    if scale.humans and scale.humans > 0:
        world.add_humans(scale.humans)

    return {
        "robot_count": len(world.robots),
        "human_count": len(world.humans),
    }


@app.post("/decision")
async def apply_decision(cmd: DecisionCommand):
    """Apply a coordination decision to a robot (from stream-processor)."""
    if not world:
        raise HTTPException(status_code=503, detail="World not initialized")

    # Check if robot has manual override (user manually stopped it)
    robot = next((r for r in world.robots if r.robot_id == cmd.robot_id), None)
    if robot and robot.manual_override:
        return {"status": "skipped", "robot_id": cmd.robot_id, "reason": "manual_override"}

    world.apply_decision(cmd.robot_id, cmd.action)
    return {"status": "applied", "robot_id": cmd.robot_id, "action": cmd.action}


class ResetRequest(BaseModel):
    """Parameters for resetting the simulation."""
    robots: int | None = None
    humans: int | None = None
    visibility: str | None = None
    connectivity: str | None = None


@app.post("/scenario/reset")
async def reset_scenario(params: ResetRequest | None = None):
    """Reset the simulation to initial state with optional parameters."""
    global world, simulation_task

    # Stop if running
    if world and world.running:
        world.running = False
        if simulation_task:
            await simulation_task
            simulation_task = None

    # Recreate world with parameters
    producer = world.producer if world else None
    robot_count = params.robots if params and params.robots else None
    human_count = params.humans if params and params.humans else None
    world = World.create(producer=producer, robot_count=robot_count, human_count=human_count)

    # Apply visibility/connectivity if specified
    if params:
        if params.visibility:
            world.visibility = params.visibility
        if params.connectivity:
            world.connectivity = params.connectivity

    return {"status": "reset", "robot_count": len(world.robots), "human_count": len(world.humans)}


@app.get("/scenario/status")
async def get_scenario_status():
    """Get current scenario status for Gemini tools."""
    if not world:
        return {"running": False, "error": "World not initialized"}

    return {
        "running": world.running,
        "sim_time": world.sim_time,
        "robot_count": len(world.robots),
        "human_count": len(world.humans),
        "robot_ids": [r.robot_id for r in world.robots],
        "visibility": world.visibility,
        "connectivity": world.connectivity,
        "congestion_level": world.congestion_level,
    }


# Individual robot control
@app.post("/robots/{robot_id}/stop")
async def stop_robot(robot_id: str):
    """Stop a specific robot (manual override - ignores stream-processor decisions)."""
    if not world:
        raise HTTPException(status_code=503, detail="World not initialized")

    robot = next((r for r in world.robots if r.robot_id == robot_id), None)
    if not robot:
        raise HTTPException(status_code=404, detail=f"Robot {robot_id} not found")

    robot.commanded_action = "STOP"
    robot.manual_override = True  # Prevent stream-processor from overriding
    return {
        "status": "stopped",
        "robot_id": robot_id,
        "commanded_action": robot.commanded_action,
        "manual_override": robot.manual_override,
    }


@app.post("/robots/{robot_id}/start")
async def start_robot(robot_id: str):
    """Resume a specific robot (clears manual override, allows stream-processor control)."""
    if not world:
        raise HTTPException(status_code=503, detail="World not initialized")

    robot = next((r for r in world.robots if r.robot_id == robot_id), None)
    if not robot:
        raise HTTPException(status_code=404, detail=f"Robot {robot_id} not found")

    robot.commanded_action = "CONTINUE"
    robot.manual_override = False  # Allow stream-processor to control again
    return {
        "status": "started",
        "robot_id": robot_id,
        "commanded_action": robot.commanded_action,
        "manual_override": robot.manual_override,
    }


@app.get("/robots/{robot_id}")
async def get_robot(robot_id: str):
    """Get detailed state of a specific robot."""
    if not world:
        raise HTTPException(status_code=503, detail="World not initialized")

    robot = next((r for r in world.robots if r.robot_id == robot_id), None)
    if not robot:
        raise HTTPException(status_code=404, detail=f"Robot {robot_id} not found")

    return {
        "robot_id": robot.robot_id,
        "x": round(robot.x, 2),
        "y": round(robot.y, 2),
        "velocity": round(robot.velocity, 2),
        "heading": round(robot.heading, 1),
        "motion_state": robot.motion_state,
        "commanded_action": robot.commanded_action,
    }
