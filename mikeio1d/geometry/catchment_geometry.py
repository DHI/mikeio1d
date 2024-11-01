"""CatchmentGeometry class."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List
from typing import Tuple

from shapely.geometry.base import BaseGeometry
from shapely.geometry import Polygon


@dataclass(frozen=True)
class CatchmentGeometry:
    """A utility class for working with catchment geometries.

    Parameters
    ----------
    points : List[Tuple[float, float]]
        List of points (x, y) defining the catchment boundary. The first and last points should be the same.

    """

    points: List[Tuple[float, float]]

    @staticmethod
    def from_res1d_catchment(res1d_catchment) -> CatchmentGeometry:
        """Create a CatchmentGeometry from an IRes1DCatchment object."""
        shape = res1d_catchment.Shape[0]  # there will always be one element
        points = []
        for i in range(shape.VertexCount()):
            vertex = shape.GetVertex(i)
            points.append((vertex.X, vertex.Y))
        return CatchmentGeometry(points)

    def to_shapely(self) -> BaseGeometry:
        """Convert to a shapely geometry."""
        return Polygon(self.points)
