"""Module for ResultNode class."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from ..res1d import Res1D
    from ..geometry import NodePoint
    from .result_quantity import ResultQuantity

    from DHI.Mike1D.ResultDataAccess import IDataItem
    from DHI.Mike1D.ResultDataAccess import IRes1DNode

from warnings import warn

from ..query import QueryDataNode
from ..various import try_import_shapely
from ..quantities import TimeSeriesIdGroup

from .result_location import ResultLocation
from .result_location import ResultLocationCreator


class ResultNode(ResultLocation):
    """Class for wrapping a single ResultData node.

    Parameters
    ----------
    node : IRes1DNode
        MIKE 1D IRes1DNode object.
    res1d : Res1D
        Res1D object the node belongs to.

    """

    def __init__(self, node, res1d):
        ResultLocation.__init__(self)

        self._group = TimeSeriesIdGroup.NODE
        self._name = node.ID

        self._creator = ResultNodeCreator(self, node, res1d)
        self._creator.create()

    def __repr__(self) -> str:
        """Return a string representation of the object."""
        return f"<{self.type}: {self.id}>"

    @property
    def res1d_node(self) -> IRes1DNode:
        """DHI.Mike1D.ResultDataAccess.IRes1DNode corresponding to this result location."""
        return self._creator.node

    @property
    def geometry(self) -> NodePoint:
        """A geometric representation of the node. Requires shapely."""
        try_import_shapely()
        from ..geometry import NodePoint

        return NodePoint.from_res1d_node(self.res1d_node)

    @property
    def id(self) -> str:
        """Node ID."""
        return self.res1d_node.ID

    @property
    def type(self) -> str:
        """Node type."""
        node_type = self.res1d_node.GetType().Name[5:]  # Removes 'Res1D' from type name
        return node_type

    @property
    def xcoord(self) -> float:
        """X coordinate of the node."""
        return self.res1d_node.XCoordinate

    @property
    def ycoord(self) -> float:
        """Y coordinate of the node."""
        return self.res1d_node.YCoordinate

    @property
    def ground_level(self) -> float | None:
        """Ground level of the node.

        Returns
        -------
            float: Ground level of the node.
            None: If the node does not have a ground level.
        """
        if hasattr(self.res1d_node, "GroundLevel"):
            return self.res1d_node.GroundLevel
        return None

    @property
    def bottom_level(self) -> float | None:
        """Bottom level of the node.

        Returns
        -------
            float: Bottom level of the node.
            None: If the node does not have a bottom level.
        """
        if hasattr(self.res1d_node, "BottomLevel"):
            return self.res1d_node.BottomLevel
        return None

    @property
    def critical_level(self) -> float | None:
        """Critical level of the node.

        Returns
        -------
            float: Critical level of the node.
            None: If the node does not have a critical level.
        """
        if hasattr(self.res1d_node, "CriticalLevel"):
            return self.res1d_node.CriticalLevel
        return None

    @property
    def diameter(self) -> float | None:
        """Diameter of the node.

        Returns
        -------
            float: Diameter of the node.
            None: If the node does not have a diameter.
        """
        if hasattr(self.res1d_node, "Diameter"):
            return self.res1d_node.Diameter
        return None

    def get_m1d_dataset(self, m1d_dataitem: IDataItem = None) -> IRes1DNode:
        """Get IRes1DDataSet object associated with ResultNode.

        Parameters
        ----------
        m1d_dataitem: IDataItem, optional
            Ignored for ResultNode.

        Returns
        -------
        IRes1DDataSet
            IRes1DDataSet object associated with ResultNode.

        """
        return self.res1d_node

    def get_query(self, data_item: IDataItem) -> QueryDataNode:
        """Get a QueryDataNode for given data item."""
        quantity_id = data_item.Quantity.Id
        node_id = self.res1d_node.ID
        query = QueryDataNode(quantity_id, node_id)
        return query


class ResultNodeCreator(ResultLocationCreator):
    """Helper class for creating ResultNode.

    Parameters
    ----------
    result_location : ResultNode
        Instance of ResultNode, which the ResultNodeCreator deals with.
    node : IRes1DNode
        MIKE 1D IRes1DNode object.
    res1d : Res1D
        Res1D object the node belongs to.

    """

    def __init__(
        self,
        result_location: ResultNode,
        node: IRes1DNode,
        res1d: Res1D,
    ):
        ResultLocationCreator.__init__(self, result_location, node.DataItems, res1d)
        self.node = node

    def create(self):
        """Perform ResultNode creation steps."""
        self.set_quantities()
        self.set_static_attributes()

    def set_static_attributes(self):
        """Set static attributes. These show up in the html repr."""
        self.set_static_attribute("id")
        self.set_static_attribute("type")
        self.set_static_attribute("xcoord")
        self.set_static_attribute("ycoord")
        self.set_static_attribute("ground_level")
        self.set_static_attribute("bottom_level")
        self.set_static_attribute("critical_level")
        self.set_static_attribute("diameter")

    def add_to_result_quantity_maps(self, quantity_id: str, result_quantity: ResultQuantity):
        """Add node result quantity to result quantity maps."""
        self.add_to_result_quantity_map(quantity_id, result_quantity, self.result_quantity_map)

        nodes_result_quantity_map = self.res1d.network.nodes._creator.result_quantity_map
        self.add_to_result_quantity_map(quantity_id, result_quantity, nodes_result_quantity_map)

        self.add_to_network_result_quantity_map(result_quantity)
