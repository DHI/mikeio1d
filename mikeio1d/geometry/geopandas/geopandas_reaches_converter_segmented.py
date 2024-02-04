from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from geopandas import GeoDataFrame
    from mikeio1d.result_network import ResultReaches

from .geopandas_converter import GeoPandasConverter
from ..reach_geometry import ReachGeometry

from mikeio1d.quantities import TimeSeriesId
from mikeio1d.quantities import TimeSeriesIdGroup


class GeopandasReachesConverterSegmented(GeoPandasConverter):
    def __init__(self):
        super().__init__()

    def _create_dataframe_data_dict(self, reaches: ResultReaches) -> dict[str, tuple]:
        data = {
            "group": [],
            "name": [],
            "tag": [],
            "geometry": [],
        }
        for reach in reaches.values():
            for m1d_reach in reach.reaches:
                data["group"].append(TimeSeriesIdGroup.REACH)
                data["name"].append(reach.name)
                data["tag"].append(TimeSeriesId.create_reach_span_tag(m1d_reach))
                data["geometry"].append(ReachGeometry.from_m1d_reaches(m1d_reach).to_shapely())
        return data

    def to_geopandas(self, reaches: ResultReaches) -> GeoDataFrame:
        data = self._create_dataframe_data_dict(reaches)
        crs = self.get_crs(reaches.res1d)
        gdf = self.gpd.GeoDataFrame(data=data, crs=crs)
        return gdf
