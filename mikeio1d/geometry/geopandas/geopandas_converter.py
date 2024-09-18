from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from geopandas import GeoDataFrame
    from pyproj import CRS

    from mikeio1d import Res1D
    from mikeio1d.result_network import ResultLocations

from abc import ABC
from abc import abstractmethod

from mikeio1d.various import pyproj_crs_from_projection_string


class GeoPandasConverter(ABC):
    """
    Abstract base class for converting to GeoPandas.
    """

    @abstractmethod
    def to_geopandas(self, reaches: ResultLocations) -> GeoDataFrame: ...

    def get_crs(self, res1d: Res1D) -> CRS | None:
        return pyproj_crs_from_projection_string(res1d.projection_string)
