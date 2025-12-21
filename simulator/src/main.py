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
        world.zone.visibility = toggle.visibility
    if toggle.connectivity:
        world.zone.connectivity = toggle.connectivity

    return {
        "visibility": world.zone.visibility,
        "connectivity": world.zone.connectivity,
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

    world.apply_decision(cmd.robot_id, cmd.action)
    return {"status": "applied", "robot_id": cmd.robot_id, "action": cmd.action}


@app.post("/scenario/reset")
async def reset_scenario():
    """Reset the simulation to initial state."""
    global world, simulation_task

    # Stop if running
    if world and world.running:
        world.running = False
        if simulation_task:
            await simulation_task
            simulation_task = None

    # Recreate world
    producer = world.producer if world else None
    world = World.create(producer=producer)

    return {"status": "reset", "robot_count": len(world.robots), "human_count": len(world.humans)}
