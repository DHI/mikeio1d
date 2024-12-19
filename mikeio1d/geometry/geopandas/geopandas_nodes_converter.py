"""GeoPandasNodesConverter class."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from geopandas import GeoDataFrame

    from ...result_network import ResultNodes

from geopandas import GeoDataFrame

from .geopandas_converter import GeoPandasConverter
from ..node_point import NodePoint

from mikeio1d.quantities import TimeSeriesIdGroup


class GeoPandasNodesConverter(GeoPandasConverter):
    """For converting ResultNodes to a GeoDataFrame.

    Example:
    -------
    >>> res = Res1D("results.res1d")
    >>> converter = GeoPandasNodesConverter()
    >>> gdf = converter.to_geopandas(res.nodes)

    """

    def __init__(self):
        super().__init__()

    def _create_dataframe_data_dict(self, nodes: ResultNodes) -> dict[str, tuple]:
        """Create a dictionary with the data needed to create a GeoDataFrame."""
        names = [node.id for node in nodes.values()]
        geometries = [
            NodePoint.from_res1d_node(node.res1d_node).to_shapely() for node in nodes.values()
        ]
        data = {
            "group": TimeSeriesIdGroup.NODE,
            "name": names,
            "geometry": geometries,
        }
        return data

    def to_geopandas(self, nodes: ResultNodes) -> GeoDataFrame:
        """Convert ResultNodes to a GeoDataFrame."""
        data = self._create_dataframe_data_dict(nodes)
        crs = self.get_crs(nodes.res1d)
        gdf = GeoDataFrame(data=data, crs=crs)
        return gdf
