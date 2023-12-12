from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from geopandas import GeoDataFrame

from ..dotnet import pythonnet_implementation as impl
from .result_locations import ResultLocations
from .result_node import ResultNode
from .various import make_proper_variable_name
from ..various import try_import_geopandas
from ..various import pyproj_crs_from_projection_string


class ResultNodes(ResultLocations):
    """
    Class for wrapping ResultData nodes.

    By itself it is also a dict, which contains
    mapping between node ID and IRes1DNode object.

    Parameters
    ----------
    res1d : Res1D
        Res1D object the nodes belong to.

    Attributes
    ----------
    node_label : str
        A label, which is appended if the node name starts
        with a number. The value used is node_label = 'n_'
    """

    def __init__(self, res1d):
        ResultLocations.__init__(self, res1d)
        self.node_label = "n_"

        res1d.result_network.nodes = self
        self.set_nodes()
        self.set_quantity_collections()

    def set_nodes(self):
        """
        Set attributes to the current ResultNodes object based
        on the node ID.
        """
        for node in self.data.Nodes:
            node = impl(node)
            result_node = ResultNode(node, self.res1d)
            self.set_res1d_node_to_dict(result_node)
            result_node_attribute_string = make_proper_variable_name(node.ID, self.node_label)
            setattr(self, result_node_attribute_string, result_node)

    def set_res1d_node_to_dict(self, result_node):
        """
        Create a dict entry from node ID to ResultNode object.
        """
        self[result_node.id] = result_node

    def to_geopandas(self) -> GeoDataFrame:
        """
        Convert nodes to a geopandas.GeoDataFrame object.

        Returns
        -------
        gdf : geopandas.GeoDataFrame
            A GeoDataFrame object with nodes as Point geometries.
        """
        gpd = try_import_geopandas()
        ids = [node.id for node in self.values()]
        geometries = [node.geometry.to_shapely() for node in self.values()]
        data = {"id": ids, "geometry": geometries}
        crs = pyproj_crs_from_projection_string(self.res1d.projection_string)
        gdf = gpd.GeoDataFrame(data=data, crs=crs)
        return gdf
