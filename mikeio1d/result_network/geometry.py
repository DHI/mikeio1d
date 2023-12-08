from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from functools import cache
from typing import Iterable, List, Protocol, Tuple

import numpy as np
import shapely
from shapely.geometry.base import BaseGeometry


class ShapelyProtocol(Protocol):
    def to_shapely(self) -> BaseGeometry:
        ...


@dataclass(frozen=True)
class NodePoint:
    """
    Create a shapely Point from an IRes1DNode object.

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
        xcoord = res1d_node.XCoordinate
        ycoord = res1d_node.YCoordinate
        return NodePoint(xcoord, ycoord)

    def to_shapely(self) -> shapely.Point:
        return shapely.Point(self.x, self.y)


class ReachPointType(Enum):
    DIGIPOINT = 0
    GRIDPOINT = 1


@dataclass(frozen=True, order=True)
class ReachPoint:
    """
    A point on a reach, either a digipoint or gridpoint.
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

    def to_shapely(self) -> shapely.Point:
        return shapely.Point(self.x, self.y)

    @staticmethod
    def from_digipoint(digipoint):
        return ReachPoint(
            ReachPointType.DIGIPOINT,
            digipoint.M,
            digipoint.X,
            digipoint.Y,
            digipoint.Z,
        )

    @staticmethod
    def from_gridpoint(gridpoint):
        return ReachPoint(
            ReachPointType.GRIDPOINT,
            gridpoint.Chainage,
            gridpoint.X,
            gridpoint.Y,
            gridpoint.Z,
        )


class ReachGeometry:
    def __init__(self, points: List[ReachPoint]):
        self._points = sorted(points)

    @staticmethod
    def from_dotnet_reaches(dotnet_reaches):
        if not isinstance(dotnet_reaches, Iterable):
            dotnet_reaches = [dotnet_reaches]

        points = []
        for reach in dotnet_reaches:
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

    def to_shapely(self) -> shapely.LineString:
        points = self._get_unique_points()
        xy = [(p.x, p.y) for p in points]
        return shapely.LineString(xy)

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

    @cache
    def _get_unique_points(self) -> List[ReachPoint]:
        return sorted(list(set(self._points)))

    @cache
    def _get_distances(self) -> List[float]:
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
    A catchment geometry.

    Parameters
    ----------
    points : List[Tuple[float, float]]
        List of points (x, y) defining the catchment boundary. The first and last points should be the same.
    """

    points: List[Tuple[float, float]]

    @staticmethod
    def from_dotnet_catchment(dotnet_catchment) -> CatchmentGeometry:
        shape = dotnet_catchment.Shape[0]  # there will always be one element
        points = []
        for i in range(shape.VertexCount()):
            vertex = shape.GetVertex(i)
            points.append((vertex.X, vertex.Y))
        return CatchmentGeometry(points)

    def to_shapely(self) -> shapely.Polygon:
        return shapely.Polygon(self.points)
