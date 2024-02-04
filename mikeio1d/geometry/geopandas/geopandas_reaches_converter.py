from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from geopandas import GeoDataFrame
    from shapely.geometry.base import BaseGeometry

    from mikeio1d.result_network import ResultReach
    from mikeio1d.result_network import ResultReaches

from .geopandas_converter import GeoPandasConverter
from ..reach_geometry import ReachGeometry

from mikeio1d.quantities import TimeSeriesIdGroup


class GeopandasReachesConverter(GeoPandasConverter):
    def __init__(self):
        super().__init__()

    def _reach_to_geometry(self, reach: ResultReach) -> ReachGeometry:
        return ReachGeometry.from_m1d_reaches(reach.reaches)

    def _reach_to_shapely(self, reach: ResultReach) -> BaseGeometry:
        return self._reach_to_geometry(reach).to_shapely()

    def to_geopandas(self, reaches: ResultReaches) -> GeoDataFrame:
        names = [reach.name for reach in reaches.values()]
        geometries = [self._reach_to_shapely(reach) for reach in reaches.values()]
        data = {
            "group": TimeSeriesIdGroup.REACH,
            "name": names,
        }
        crs = self.get_crs(reaches.res1d)
        gdf = self.gpd.GeoDataFrame(data=data, crs=crs, geometry=geometries)
        return gdf
