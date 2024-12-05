"""GeioPandasReachesConverter class."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from geopandas import GeoDataFrame
    from shapely.geometry.base import BaseGeometry

    from mikeio1d.result_network import ResultReach
    from mikeio1d.result_network import ResultReaches

from geopandas import GeoDataFrame

from .geopandas_converter import GeoPandasConverter
from ..reach_geometry import ReachGeometry

from mikeio1d.quantities import TimeSeriesIdGroup


class GeoPandasReachesConverter(GeoPandasConverter):
    """For converting ResultReaches to a GeoDataFrame.

    Each unique ResultReach name will be a row in the GeoDataFrame.

    Example:
    -------
    >>> res = Res1D("results.res1d")
    >>> converter = GeopandasReachesConverter()
    >>> gdf = converter.to_geopandas(res.reaches)

    """

    def __init__(self):
        super().__init__()

    def _reach_to_geometry(self, reach: ResultReach) -> ReachGeometry:
        return ReachGeometry.from_res1d_reaches(reach.res1d_reaches)

    def _reach_to_shapely(self, reach: ResultReach) -> BaseGeometry:
        return self._reach_to_geometry(reach).to_shapely()

    def _create_dataframe_data_dict(self, reaches: ResultReaches) -> dict[str, tuple]:
        """Create a dictionary with the data needed to create a GeoDataFrame."""
        names = [reach.name for reach in reaches.values()]
        geometries = [self._reach_to_shapely(reach) for reach in reaches.values()]
        data = {
            "group": TimeSeriesIdGroup.REACH,
            "name": names,
            "geometry": geometries,
        }
        return data

    def to_geopandas(self, reaches: ResultReaches) -> GeoDataFrame:
        """Convert ResultReaches to a GeoDataFrame."""
        data = self._create_dataframe_data_dict(reaches)
        crs = self.get_crs(reaches.res1d)
        gdf = GeoDataFrame(data=data, crs=crs)
        return gdf
