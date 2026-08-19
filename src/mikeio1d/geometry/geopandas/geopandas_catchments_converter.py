"""GeoPandasCatchmentsConverter class."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from geopandas import GeoDataFrame

    from ...result_network import ResultCatchments

from geopandas import GeoDataFrame

from .geopandas_converter import GeoPandasConverter
from ..catchment_geometry import CatchmentGeometry

from mikeio1d.quantities import TimeSeriesIdGroup


class GeoPandasCatchmentsConverter(GeoPandasConverter):
    """For converting ResultCatchments to a GeoDataFrame.

    Example:
    -------
    >>> res = Res1D("results.res1d")
    >>> converter = GeoPandasCatchmentsConverter()
    >>> gdf = converter.to_geopandas(res.catchments)

    """

    def __init__(self):
        super().__init__()

    def _create_dataframe_data_dict(self, catchments: ResultCatchments) -> dict[str, tuple]:
        """Create a dictionary with the data needed to create a GeoDataFrame."""
        names = [catchment.id for catchment in catchments.values()]
        geometries = [
            CatchmentGeometry.from_res1d_catchment(catchment.res1d_catchment).to_shapely()
            for catchment in catchments.values()
        ]
        data = {
            "group": TimeSeriesIdGroup.CATCHMENT,
            "name": names,
            "geometry": geometries,
        }
        return data

    def to_geopandas(self, catchments: ResultCatchments) -> GeoDataFrame:
        """Convert ResultCatchments to a GeoDataFrame."""
        data = self._create_dataframe_data_dict(catchments)
        crs = self.get_crs(catchments.res1d)
        gdf = GeoDataFrame(data=data, crs=crs)
        return gdf
