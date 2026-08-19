"""ReachPoint class."""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from enum import Enum

from shapely.geometry.base import BaseGeometry
from shapely.geometry import Point


class ReachPointType(Enum):
    """Enum for the type of reach point."""

    DIGIPOINT = 0
    GRIDPOINT = 1


@dataclass(frozen=True, order=True)
class ReachPoint:
    """A utility class for working with points along a reach.

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
        """Check if the point is a digipoint."""
        return self.point_type == ReachPointType.DIGIPOINT

    def is_gridpoint(self):
        """Check if the point is a gridpoint."""
        return self.point_type == ReachPointType.GRIDPOINT

    def to_shapely(self) -> BaseGeometry:
        """Convert to a Shapely Point."""
        return Point(self.x, self.y)

    @staticmethod
    def from_digipoint(res1d_digipoint):
        """Create a ReachPoint from an IRes1DDigiPoint object."""
        return ReachPoint(
            ReachPointType.DIGIPOINT,
            res1d_digipoint.M,
            res1d_digipoint.X,
            res1d_digipoint.Y,
            res1d_digipoint.Z,
        )

    @staticmethod
    def from_gridpoint(res1d_gridpoint):
        """Create a ReachPoint from an IRes1DGridPoint object."""
        return ReachPoint(
            ReachPointType.GRIDPOINT,
            res1d_gridpoint.Chainage,
            res1d_gridpoint.X,
            res1d_gridpoint.Y,
            res1d_gridpoint.Z,
        )
