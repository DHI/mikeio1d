from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from functools import lru_cache
from typing import Iterable
from typing import List
from typing import Protocol
from typing import Tuple

import numpy as np
from shapely.geometry.base import BaseGeometry
from shapely.geometry import Point
from shapely.geometry import LineString
from shapely.geometry import Polygon


class ReachPointType(Enum):
    DIGIPOINT = 0
    GRIDPOINT = 1


class ConvertableToShapely(Protocol):
    def to_shapely(self) -> BaseGeometry:
        ...


@dataclass(frozen=True)
class NodePoint:
    """
    A utility class for working with node geometries.

    Parameters
    ----------
    x : float
        X coordinate
    y : float
        Y coordinate
    """

    x: float
    y: float

    @staticmethod
    def from_res1d_node(res1d_node) -> NodePoint:
        """
        Create a NodePoint from an IRes1DNode object.
        """
        xcoord = res1d_node.XCoordinate
        ycoord = res1d_node.YCoordinate
        return NodePoint(xcoord, ycoord)

    def to_shapely(self) -> BaseGeometry:
        return Point(self.x, self.y)


@dataclass(frozen=True, order=True)
class ReachPoint:
    """
    A utility class for working with points along a reach.

    Parameters
    ----------
    point_type : ReachPointType
        Either DIGIPOINT or GRIDPOINT
    chainage : float
        Chainage along the reach. Need not match geometric distance.
    x : float
        X coordinate
    y : float
        Y coordinate
    z : float
        Z coordinate
    """

    point_type: ReachPointType = field(compare=False)
    chainage: float
    x: float
    y: float
    z: float

    def is_digipoint(self):
        return self.point_type == ReachPointType.DIGIPOINT

    def is_gridpoint(self):
        return self.point_type == ReachPointType.GRIDPOINT

    def to_shapely(self) -> BaseGeometry:
        return Point(self.x, self.y)

    @staticmethod
    def from_digipoint(res1d_digipoint):
        """
        Create a ReachPoint from an IRes1DDigiPoint object.
        """
        return ReachPoint(
            ReachPointType.DIGIPOINT,
            res1d_digipoint.M,
            res1d_digipoint.X,
            res1d_digipoint.Y,
            res1d_digipoint.Z,
        )

    @staticmethod
    def from_gridpoint(res1d_gridpoint):
        """
        Create a ReachPoint from an IRes1DGridPoint object.
        """
        return ReachPoint(
            ReachPointType.GRIDPOINT,
            res1d_gridpoint.Chainage,
            res1d_gridpoint.X,
            res1d_gridpoint.Y,
            res1d_gridpoint.Z,
        )


class ReachGeometry:
    """
    A utility class for working with reach geometries.
    """

    def __init__(self, points: List[ReachPoint]):
        self._points = sorted(points)

    @staticmethod
    def from_res1d_reaches(res1d_reaches):
        """
        Create a ReachGeometry from a list of IRes1DReach objects.

        Parameters
        ----------
        res1d_reaches : List[IRes1DReach]
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
        return [p.chainage for p in self._get_unique_points()]

    @property
    def points(self) -> List[ReachPoint]:
        return self._points

    @property
    def digipoints(self) -> List[ReachPoint]:
        return [p for p in self.points if p.is_digipoint()]

    @property
    def gridpoints(self) -> List[ReachPoint]:
        return [p for p in self.points if p.is_gridpoint()]

    @property
    def length(self) -> float:
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
        """Removes points sharing the same chainage and coordinates."""
        return sorted(list(set(self._points)))

    @lru_cache(maxsize=None)
    def _get_distances(self) -> List[float]:
        """Returns a list of geometric distances between all unique points."""
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


@dataclass(frozen=True)
class CatchmentGeometry:
    """
    A utility class for working with catchment geometries.

    Parameters
    ----------
    points : List[Tuple[float, float]]
        List of points (x, y) defining the catchment boundary. The first and last points should be the same.
    """

    points: List[Tuple[float, float]]

    @staticmethod
    def from_res1d_catchment(res1d_catchment) -> CatchmentGeometry:
        """
        Create a CatchmentGeometry from an IRes1DCatchment object.
        """
        shape = res1d_catchment.Shape[0]  # there will always be one element
        points = []
        for i in range(shape.VertexCount()):
            vertex = shape.GetVertex(i)
            points.append((vertex.X, vertex.Y))
        return CatchmentGeometry(points)

    def to_shapely(self) -> BaseGeometry:
        """Convert to a shapely geometry."""
        return Polygon(self.points)
