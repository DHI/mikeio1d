"""CrossSectionGeometry class."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import List
    from typing import Tuple

from shapely.geometry.base import BaseGeometry
from shapely.geometry import LineString


class CrossSectionGeometry:
    """A utility class for working with cross section geometries.

    Parameters
    ----------
    m1d_cross_section : ICrossSection
        A cross section from MIKE 1D.

    """

    def __init__(self, m1d_cross_section):
        self._m1d_cross_section = m1d_cross_section

    @property
    def coords(self) -> List[Tuple[float, float]]:
        """Get the coordinates of the cross section.

        Returns
        -------
        list of tuples
            List of (x, y) coordinates.

        """
        if self._m1d_cross_section.Coordinates is None:
            return []
        return [(p.X, p.Y) for p in self._m1d_cross_section.Coordinates]

    def to_shapely(self) -> BaseGeometry:
        """Convert the cross section to a Shapely LineString."""
        return LineString(self.coords)
