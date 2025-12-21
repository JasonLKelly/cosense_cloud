"""
A* Pathfinding for warehouse robots.

Grid-based pathfinding that avoids obstacles and can handle dynamic obstacles.
"""

import heapq
import math
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PathNode:
    """Node in the pathfinding grid."""
    x: int
    y: int
    g: float = float('inf')  # Cost from start
    h: float = 0             # Heuristic (estimated cost to goal)
    parent: Optional['PathNode'] = field(default=None, repr=False)

    @property
    def f(self) -> float:
        """Total estimated cost."""
        return self.g + self.h

    def __lt__(self, other: 'PathNode') -> bool:
        return self.f < other.f

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, PathNode):
            return False
        return self.x == other.x and self.y == other.y

    def __hash__(self) -> int:
        return hash((self.x, self.y))


class Pathfinder:
    """A* pathfinding on a warehouse grid."""

    # 8-directional movement (including diagonals)
    DIRECTIONS = [
        (0, -1, 1.0),    # North
        (1, 0, 1.0),     # East
        (0, 1, 1.0),     # South
        (-1, 0, 1.0),    # West
        (1, -1, 1.414),  # NE
        (1, 1, 1.414),   # SE
        (-1, 1, 1.414),  # SW
        (-1, -1, 1.414), # NW
    ]

    def __init__(
        self,
        width: int,
        height: int,
        obstacles: set[tuple[int, int]],
        resolution: float = 0.5,
    ):
        """
        Initialize pathfinder.

        Args:
            width: Grid width in cells
            height: Grid height in cells
            obstacles: Set of (x, y) cells that are blocked
            resolution: Meters per grid cell
        """
        self.width = width
        self.height = height
        self.obstacles = obstacles
        self.resolution = resolution
        self.dynamic_obstacles: set[tuple[int, int]] = set()

    def world_to_grid(self, x: float, y: float) -> tuple[int, int]:
        """Convert world coordinates to grid coordinates."""
        return (int(x / self.resolution), int(y / self.resolution))

    def grid_to_world(self, gx: int, gy: int) -> tuple[float, float]:
        """Convert grid coordinates to world coordinates (center of cell)."""
        return (
            (gx + 0.5) * self.resolution,
            (gy + 0.5) * self.resolution,
        )

    def is_walkable(self, x: int, y: int) -> bool:
        """Check if a grid cell is walkable."""
        if x < 0 or x >= self.width or y < 0 or y >= self.height:
            return False
        if (x, y) in self.obstacles:
            return False
        if (x, y) in self.dynamic_obstacles:
            return False
        return True

    def set_dynamic_obstacles(self, obstacles: set[tuple[int, int]]):
        """Update dynamic obstacles (other robots, temporary blocks)."""
        self.dynamic_obstacles = obstacles

    def heuristic(self, x1: int, y1: int, x2: int, y2: int) -> float:
        """Euclidean distance heuristic."""
        return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

    def find_path(
        self,
        start_x: float,
        start_y: float,
        goal_x: float,
        goal_y: float,
    ) -> list[tuple[float, float]]:
        """
        Find a path from start to goal in world coordinates.

        Returns:
            List of (x, y) waypoints in world coordinates, or empty list if no path.
        """
        # Convert to grid coordinates
        sx, sy = self.world_to_grid(start_x, start_y)
        gx, gy = self.world_to_grid(goal_x, goal_y)

        # Check if start and goal are valid
        if not self.is_walkable(sx, sy):
            # Try to find nearest walkable cell to start
            sx, sy = self._find_nearest_walkable(sx, sy)
            if sx is None:
                return []

        if not self.is_walkable(gx, gy):
            # Try to find nearest walkable cell to goal
            gx, gy = self._find_nearest_walkable(gx, gy)
            if gx is None:
                return []

        # A* algorithm
        start_node = PathNode(sx, sy, g=0, h=self.heuristic(sx, sy, gx, gy))
        goal_node = PathNode(gx, gy)

        open_set: list[PathNode] = [start_node]
        closed_set: set[tuple[int, int]] = set()
        node_map: dict[tuple[int, int], PathNode] = {(sx, sy): start_node}

        while open_set:
            current = heapq.heappop(open_set)

            if current.x == gx and current.y == gy:
                # Found path - reconstruct it
                return self._reconstruct_path(current)

            closed_set.add((current.x, current.y))

            for dx, dy, cost in self.DIRECTIONS:
                nx, ny = current.x + dx, current.y + dy

                if not self.is_walkable(nx, ny):
                    continue
                if (nx, ny) in closed_set:
                    continue

                # Check diagonal movement doesn't cut corners
                if dx != 0 and dy != 0:
                    if not self.is_walkable(current.x + dx, current.y) or \
                       not self.is_walkable(current.x, current.y + dy):
                        continue

                tentative_g = current.g + cost

                if (nx, ny) not in node_map:
                    node_map[(nx, ny)] = PathNode(nx, ny)

                neighbor = node_map[(nx, ny)]

                if tentative_g < neighbor.g:
                    neighbor.g = tentative_g
                    neighbor.h = self.heuristic(nx, ny, gx, gy)
                    neighbor.parent = current

                    if neighbor not in open_set:
                        heapq.heappush(open_set, neighbor)

        # No path found
        return []

    def _reconstruct_path(self, node: PathNode) -> list[tuple[float, float]]:
        """Reconstruct path from goal node to start."""
        path = []
        current: Optional[PathNode] = node

        while current is not None:
            wx, wy = self.grid_to_world(current.x, current.y)
            path.append((wx, wy))
            current = current.parent

        path.reverse()
        return self._smooth_path(path)

    def _smooth_path(self, path: list[tuple[float, float]]) -> list[tuple[float, float]]:
        """Remove unnecessary waypoints from path."""
        if len(path) <= 2:
            return path

        smoothed = [path[0]]

        i = 0
        while i < len(path) - 1:
            # Try to skip waypoints if direct path is clear
            j = len(path) - 1
            while j > i + 1:
                if self._line_of_sight(path[i], path[j]):
                    break
                j -= 1
            smoothed.append(path[j])
            i = j

        return smoothed

    def _line_of_sight(self, p1: tuple[float, float], p2: tuple[float, float]) -> bool:
        """Check if there's a clear line of sight between two points."""
        x1, y1 = self.world_to_grid(p1[0], p1[1])
        x2, y2 = self.world_to_grid(p2[0], p2[1])

        dx = abs(x2 - x1)
        dy = abs(y2 - y1)
        sx = 1 if x1 < x2 else -1
        sy = 1 if y1 < y2 else -1
        err = dx - dy

        while True:
            if not self.is_walkable(x1, y1):
                return False
            if x1 == x2 and y1 == y2:
                return True

            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x1 += sx
            if e2 < dx:
                err += dx
                y1 += sy

    def _find_nearest_walkable(self, x: int, y: int, max_dist: int = 10) -> tuple[int, int] | tuple[None, None]:
        """Find nearest walkable cell to given position."""
        for dist in range(1, max_dist + 1):
            for dx in range(-dist, dist + 1):
                for dy in range(-dist, dist + 1):
                    if abs(dx) == dist or abs(dy) == dist:
                        nx, ny = x + dx, y + dy
                        if self.is_walkable(nx, ny):
                            return nx, ny
        return None, None


def create_pathfinder_from_map(map_data: dict) -> Pathfinder:
    """Create a Pathfinder from a warehouse map definition."""
    width = map_data["width"]
    height = map_data["height"]
    resolution = map_data.get("grid_resolution", 0.5)

    # Convert dimensions to grid cells
    grid_width = int(width / resolution)
    grid_height = int(height / resolution)

    # Build obstacle set from map obstacles
    obstacles: set[tuple[int, int]] = set()

    for obs in map_data.get("obstacles", []):
        obs_type = obs["type"]
        # Only block movement for certain obstacle types
        if obs_type in ("rack", "wall", "conveyor", "workstation"):
            x1 = int(obs["x"] / resolution)
            y1 = int(obs["y"] / resolution)
            x2 = int((obs["x"] + obs["width"]) / resolution)
            y2 = int((obs["y"] + obs["height"]) / resolution)

            for gx in range(x1, x2):
                for gy in range(y1, y2):
                    obstacles.add((gx, gy))

    return Pathfinder(grid_width, grid_height, obstacles, resolution)
