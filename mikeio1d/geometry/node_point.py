"""NodePoint class."""

from __future__ import annotations

from dataclasses import dataclass

from shapely.geometry.base import BaseGeometry
from shapely.geometry import Point


@dataclass(frozen=True)
class NodePoint:
    """A utility class for working with node geometries.

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
        """Create a NodePoint from an IRes1DNode object."""
        xcoord = res1d_node.XCoordinate
        ycoord = res1d_node.YCoordinate
        return NodePoint(xcoord, ycoord)

    def to_shapely(self) -> BaseGeometry:
        """Convert to a Shapely Point."""
        return Point(self.x, self.y)
