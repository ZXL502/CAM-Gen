from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Sequence, Tuple

import numpy as np


Point = Tuple[float, float, float]


def _generate_line_samples(p1: Point, p2: Point, step: float = 0.5) -> Iterable[Point]:
    vector = np.array(p2) - np.array(p1)
    length = np.linalg.norm(vector)
    if length == 0:
        yield p1
        return

    num_steps = max(int(length / step), 1)
    for t in np.linspace(0, 1, num_steps + 1):
        yield tuple(np.array(p1) + vector * t)


def _bounding_box(center: np.ndarray, radius: float, resolution: int) -> Tuple[np.ndarray, np.ndarray]:
    min_corner = np.floor(center - radius).astype(int)
    max_corner = np.ceil(center + radius).astype(int)
    min_corner = np.clip(min_corner, 0, resolution - 1)
    max_corner = np.clip(max_corner, 0, resolution - 1)
    return min_corner, max_corner


def _is_cutting_move(p1: Point, p2: Point) -> bool:
    return p1 != p2


@dataclass
class SimulationResult:
    remaining: np.ndarray
    removed_volume: float
    collision: bool


class VoxelSimulator:
    """Boolean voxel subtractor inspired by Shape2GCode Appendix A.2."""

    def __init__(self, resolution: int = 128):
        self.resolution = resolution
        self.grid = np.ones((resolution, resolution, resolution), dtype=bool)
        self.removed_volume = 0.0
        self.collision = False

    def simulate_toolpath(self, toolpath_points: Sequence[Point], tool_radius: float) -> SimulationResult:
        if len(toolpath_points) < 2:
            return SimulationResult(self.grid.copy(), self.removed_volume, self.collision)

        for start, end in zip(toolpath_points[:-1], toolpath_points[1:]):
            if _is_cutting_move(start, end):
                self._remove_material(start, end, tool_radius)
        return SimulationResult(self.grid.copy(), self.removed_volume, self.collision)

    def _remove_material(self, p1: Point, p2: Point, tool_radius: float) -> None:
        for sample in _generate_line_samples(p1, p2):
            center = np.array(sample)
            min_corner, max_corner = _bounding_box(center, tool_radius, self.resolution)
            slices = tuple(slice(min_corner[i], max_corner[i] + 1) for i in range(3))

            region = self.grid[slices]
            coords = np.argwhere(region)
            if coords.size == 0:
                continue

            coords_world = coords + min_corner
            distances = np.linalg.norm(coords_world - center, axis=1)
            within_radius = distances <= tool_radius
            if not np.any(within_radius):
                continue

            to_remove = tuple(coords_world[within_radius].T)
            before = len(to_remove[0])
            self.grid[to_remove] = False
            self.removed_volume += before

    def simulate_revolve_2d(self, path_points: Sequence[Tuple[float, float]], tool_radius: float) -> SimulationResult:
        if len(path_points) < 2:
            return SimulationResult(self.grid.copy(), self.removed_volume, self.collision)

        xz_grid = np.ones((self.resolution, self.resolution), dtype=bool)
        for (x1, z1), (x2, z2) in zip(path_points[:-1], path_points[1:]):
            if (x1, z1) == (x2, z2):
                continue
            for sample in _generate_line_samples((x1, 0.0, z1), (x2, 0.0, z2)):
                center = np.array([sample[0], sample[2]])
                min_corner, max_corner = _bounding_box(center, tool_radius, self.resolution)
                slices = (slice(min_corner[0], max_corner[0] + 1), slice(min_corner[1], max_corner[1] + 1))
                region = xz_grid[slices]
                coords = np.argwhere(region)
                if coords.size == 0:
                    continue
                coords_world = coords + min_corner
                distances = np.linalg.norm(coords_world - center, axis=1)
                within_radius = distances <= tool_radius
                if not np.any(within_radius):
                    continue
                to_remove = tuple(coords_world[within_radius].T)
                before = len(to_remove[0])
                xz_grid[to_remove] = False
                self.removed_volume += before

        extruded = np.repeat(xz_grid[:, np.newaxis, :], self.resolution, axis=1)
        return SimulationResult(extruded, self.removed_volume, self.collision)
