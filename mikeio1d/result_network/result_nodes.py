from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from typing import Dict
    from typing import Callable
    from geopandas import GeoDataFrame

from ..dotnet import pythonnet_implementation as impl
from .result_locations import ResultLocations
from .result_node import ResultNode
from .various import make_proper_variable_name
from ..pandas_extension import ResultFrameAggregator
from ..quantities import TimeSeriesIdGroup


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
        self._group = TimeSeriesIdGroup.NODE
        self.node_label = "n_"

        res1d.result_network.nodes = self
        self.set_nodes()
        self.set_quantity_collections()

        self._node_ids = None
        self._geometries = None

    def set_nodes(self):
        """
        Set attributes to the current ResultNodes object based
        on the node ID.
        """
        for node in self.data.Nodes:
            node = impl(node)
            result_node = ResultNode(node, self.res1d)
            self.set_res1d_node_to_dict(result_node)
            result_node_attribute_string = make_proper_variable_name(
                node.ID, self.node_label
            )
            setattr(self, result_node_attribute_string, result_node)

    def set_res1d_node_to_dict(self, result_node):
        """
        Create a dict entry from node ID to ResultNode object.
        """
        self[result_node.id] = result_node

    def to_geopandas(
        self,
        agg: str | Callable = None,
        agg_kwargs: Dict[str : str | Callable] = {},
        include_derived: bool = False,
    ) -> GeoDataFrame:
        """
        Convert nodes to a geopandas.GeoDataFrame, optionally with quantities.

        By default, quantities are not included. To include quantities, use the `agg` and `agg_kwargs` parameters.

        Parameters
        ----------
        agg : str or callable, default None
            Defines how to aggregate the quantities in time and space.
            Accepts any str or callable that is accepted by pandas.DataFrame.agg.

            Examples:
            - 'mean'  : mean value of all quantities
            - 'max'   : maximum value of all quantities
            -  np.max : maximum value of all quantities

        agg_kwargs : dict, default {}
            Aggregation function for specific column levels (e.g. {time='min', chainage='first'}).
        include_derived: bool, default False
            Include derived quantities.

        Returns
        -------
        gdf : geopandas.GeoDataFrame
            A GeoDataFrame object with nodes as Point geometries.

        Examples
        --------
        # Convert nodes to a GeoDataFrame (without quantities)
        >>> gdf = res1d.result_network.nodes.to_geopandas()

        # Convert nodes to a GeoDataFrame (with quantities)
        >>> gdf = res1d.result_network.nodes.to_geopandas(agg='mean')
        """
        from ..geometry.geopandas import GeoPandasNodesConverter

        gpd_converter = GeoPandasNodesConverter()
        gdf = gpd_converter.to_geopandas(self)

        if agg is None:
            return gdf

        rfa = ResultFrameAggregator(agg, **agg_kwargs)

        df_quantities = self.read(
            column_mode="compact", include_derived=include_derived
        )
        df_quantities = rfa.aggregate(df_quantities)

        gdf = gdf.merge(df_quantities, left_on="name", right_index=True)

        return gdf
