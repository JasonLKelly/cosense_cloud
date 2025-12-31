"""
Warehouse Map Schema

Defines the structure for warehouse layouts used by simulator and webapp.
Grid-based system optimized for A* pathfinding.
"""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class CellType(str, Enum):
    """Types of cells in the warehouse grid."""
    FLOOR = "floor"           # Walkable corridor
    RACK = "rack"             # Storage rack (obstacle)
    CONVEYOR = "conveyor"     # Conveyor belt (obstacle, robots avoid)
    WORKSTATION = "workstation"  # Packing/processing station
    DOCK = "dock"             # Loading dock
    WALL = "wall"             # Wall/boundary
    CHARGING = "charging"     # Robot charging station


class Direction(str, Enum):
    """Direction for conveyors and one-way paths."""
    NORTH = "north"
    SOUTH = "south"
    EAST = "east"
    WEST = "west"


class Waypoint(BaseModel):
    """Named location robots can navigate to."""
    id: str
    name: str
    x: float  # meters
    y: float  # meters


class Obstacle(BaseModel):
    """A rectangular obstacle (rack, conveyor, workstation)."""
    id: str
    type: CellType
    x: float      # top-left corner, meters
    y: float
    width: float  # meters
    height: float
    label: Optional[str] = None
    color: Optional[str] = None
    direction: Optional[Direction] = None  # for conveyors


class WarehouseMap(BaseModel):
    """Complete warehouse map definition."""
    id: str
    name: str
    version: str = "1.0"

    # Dimensions in meters
    width: float
    height: float

    # Grid resolution for pathfinding (meters per cell)
    grid_resolution: float = 0.5

    # Obstacles (racks, conveyors, workstations, walls)
    obstacles: list[Obstacle] = Field(default_factory=list)

    # Named waypoints for navigation
    waypoints: list[Waypoint] = Field(default_factory=list)

    def to_grid(self) -> list[list[CellType]]:
        """Convert map to grid for pathfinding."""
        cols = int(self.width / self.grid_resolution)
        rows = int(self.height / self.grid_resolution)

        # Initialize all cells as floor
        grid = [[CellType.FLOOR for _ in range(cols)] for _ in range(rows)]

        # Mark obstacles
        for obs in self.obstacles:
            x1 = int(obs.x / self.grid_resolution)
            y1 = int(obs.y / self.grid_resolution)
            x2 = int((obs.x + obs.width) / self.grid_resolution)
            y2 = int((obs.y + obs.height) / self.grid_resolution)

            for row in range(max(0, y1), min(rows, y2)):
                for col in range(max(0, x1), min(cols, x2)):
                    grid[row][col] = obs.type

        return grid

    def is_walkable(self, x: float, y: float) -> bool:
        """Check if a position is walkable."""
        for obs in self.obstacles:
            if (obs.x <= x < obs.x + obs.width and
                obs.y <= y < obs.y + obs.height and
                obs.type in (CellType.RACK, CellType.WALL, CellType.CONVEYOR)):
                return False
        return 0 <= x < self.width and 0 <= y < self.height

    def get_waypoint(self, waypoint_id: str) -> Optional[Waypoint]:
        """Get waypoint by ID."""
        for wp in self.waypoints:
            if wp.id == waypoint_id:
                return wp
        return None
