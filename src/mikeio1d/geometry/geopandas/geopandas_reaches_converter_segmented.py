"""GeoPandasReachesConverterSegmented class."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from geopandas import GeoDataFrame
    from mikeio1d.result_network import ResultReaches

from geopandas import GeoDataFrame

from .geopandas_converter import GeoPandasConverter
from ..reach_geometry import ReachGeometry

from mikeio1d.quantities import TimeSeriesId
from mikeio1d.quantities import TimeSeriesIdGroup


class GeoPandasReachesConverterSegmented(GeoPandasConverter):
    """For converting ResultReaches to a GeoDataFrame.

    Each ResultReach will be split into segments and each segment will be a row in the GeoDataFrame.
    Segments are based on the IRes1DReaches in ResultReach.reaches.

    Example:
    -------
    >>> res = Res1D("results.res1d")
    >>> converter = GeopandasReachesConverterSegmented()
    >>> gdf = converter.to_geopandas(res.reaches)

    """

    def __init__(self):
        super().__init__()

    def _create_dataframe_data_dict(self, reaches: ResultReaches) -> dict[str, tuple]:
        """Create a dictionary with the data needed to create a GeoDataFrame."""
        data = {
            "group": [],
            "name": [],
            "tag": [],
            "geometry": [],
        }
        for reach in reaches.values():
            for res1d_reach in reach.res1d_reaches:
                data["group"].append(TimeSeriesIdGroup.REACH)
                data["name"].append(reach.name)
                data["tag"].append(TimeSeriesId.create_reach_span_tag(res1d_reach))
                data["geometry"].append(ReachGeometry.from_res1d_reaches(res1d_reach).to_shapely())
        return data

    def to_geopandas(self, reaches: ResultReaches) -> GeoDataFrame:
        """Convert ResultReaches to a GeoDataFrame."""
        data = self._create_dataframe_data_dict(reaches)
        crs = self.get_crs(reaches.res1d)
        gdf = GeoDataFrame(data=data, crs=crs)
        return gdf
