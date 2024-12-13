"""ReachGeometry class."""

from __future__ import annotations

from functools import lru_cache
from typing import Iterable
from typing import List

import numpy as np
from shapely.geometry.base import BaseGeometry
from shapely.geometry import LineString

from .reach_point import ReachPoint


class ReachGeometry:
    """A utility class for working with reach geometries."""

    def __init__(self, points: List[ReachPoint]):
        self._points = sorted(points)

    @staticmethod
    def from_res1d_reaches(res1d_reaches) -> ReachGeometry:
        """Create a ReachGeometry from a list of IRes1DReach objects.

        Parameters
        ----------
        res1d_reaches : IRes1DReach | List[IRes1DReach]

        Returns
        -------
        ReachGeometry

        """
        if not isinstance(res1d_reaches, Iterable):
            res1d_reaches = [res1d_reaches]

        points = []
        for reach in res1d_reaches:
            points.extend([ReachPoint.from_digipoint(dp) for dp in reach.DigiPoints])
            points.extend([ReachPoint.from_gridpoint(gp) for gp in reach.GridPoints])

        return ReachGeometry(points)

    @property
    def chainages(self) -> List[float]:
        """List of unique chainages."""
        return [p.chainage for p in self._get_unique_points()]

    @property
    def points(self) -> List[ReachPoint]:
        """List of unique points."""
        return self._points

    @property
    def digipoints(self) -> List[ReachPoint]:
        """List of digipoints."""
        return [p for p in self.points if p.is_digipoint()]

    @property
    def gridpoints(self) -> List[ReachPoint]:
        """List of gridpoints."""
        return [p for p in self.points if p.is_gridpoint()]

    @property
    def length(self) -> float:
        """Length of the reach."""
        return self.chainages[-1] - self.chainages[0]

    def to_shapely(self) -> BaseGeometry:
        """Convert to a shapely geometry."""
        points = self._get_unique_points()
        xy = [(p.x, p.y) for p in points]
        return LineString(xy)

    def chainage_to_geometric_distance(self, chainage: float) -> float:
        """Convert chainage to geometric distance."""
        chainages = self.chainages
        distances = self._get_distances()
        if chainage < chainages[0] or chainage > chainages[-1]:
            raise ValueError(
                f"Chainage of {chainage} outside reach range of {chainages[0]} to {chainages[-1]}"
            )
        distance = float(np.interp(chainage, chainages, distances))
        return distance

    def chainage_from_geometric_distance(self, geometric_distance: float) -> float:
        """Convert geometric distance to chainage."""
        chainages = self.chainages
        distances = self._get_distances()
        if geometric_distance < distances[0] or geometric_distance > distances[-1]:
            raise ValueError(
                f"Geometric distance of {geometric_distance} outside reach range of {distances[0]} to {distances[-1]}"
            )
        chainage = float(np.interp(geometric_distance, distances, chainages))
        return chainage

    @lru_cache(maxsize=None)
    def _get_unique_points(self) -> List[ReachPoint]:
        """Remove points sharing the same chainage and coordinates."""
        return sorted(list(set(self._points)))

    @lru_cache(maxsize=None)
    def _get_distances(self) -> List[float]:
        """Return a list of geometric distances between all unique points."""
        points = self._get_unique_points()
        distances = []
        total_distance = 0.0
        prev_point = points[0]
        for point in points:
            distance = point.to_shapely().distance(prev_point.to_shapely())
            total_distance += distance
            distances.append(total_distance)
            prev_point = point
        return distances
