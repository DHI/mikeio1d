"""Module for ResultNode class."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from ..geometry import NodePoint

from warnings import warn

from ..query import QueryDataNode
from .result_location import ResultLocation
from ..various import try_import_shapely
from ..quantities import TimeSeriesIdGroup


class ResultNode(ResultLocation):
    """Class for wrapping a single ResultData node.

    Parameters
    ----------
    res1d : Res1D
        Res1D object the node belongs to.

    """

    def __init__(self, node, res1d):
        ResultLocation.__init__(self, node.DataItems, res1d)
        self._group = TimeSeriesIdGroup.NODE
        self._name = node.ID
        self._node = node
        self.set_quantities()
        self.set_static_attributes()

    def __repr__(self) -> str:
        """Return a string representation of the object."""
        return f"<{self.type}: {self.id}>"

    def __getattr__(self, name: str):
        """Warn if accessing deprecated attributes."""
        # TODO: Remove this in 1.0.0
        if name == "node":
            warn("Accessing IRes1DNode attribute via .node is deprecated. Use ._node.")
            return self._node
        elif hasattr(self._node, name):
            warn(
                f"Accessing IRes1DNode attribute {name} directly is deprecated. Use static attributes instead, or ._node.{name}."
            )
            return getattr(self._node, name)
        else:
            object.__getattribute__(self, name)

    def get_m1d_dataset(self, m1d_dataitem=None):
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
        return self._node

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

    def add_to_result_quantity_maps(self, quantity_id, result_quantity):
        """Add node result quantity to result quantity maps."""
        self.add_to_result_quantity_map(quantity_id, result_quantity, self.result_quantity_map)

        nodes_result_quantity_map = self.res1d.network.nodes.result_quantity_map
        self.add_to_result_quantity_map(quantity_id, result_quantity, nodes_result_quantity_map)

        self.add_to_network_result_quantity_map(result_quantity)

    def get_query(self, data_item):
        """Get a QueryDataNode for given data item."""
        quantity_id = data_item.Quantity.Id
        node_id = self._node.ID
        query = QueryDataNode(quantity_id, node_id)
        return query

    @property
    def geometry(self) -> NodePoint:
        """A geometric representation of the node. Requires shapely."""
        try_import_shapely()
        from ..geometry import NodePoint

        return NodePoint.from_res1d_node(self._node)

    @property
    def id(self) -> str:
        """Node ID."""
        return self._node.ID

    @property
    def type(self) -> str:
        """Node type."""
        node_type = self._node.GetType().Name[5:]  # Removes 'Res1D' from type name
        return node_type

    @property
    def xcoord(self) -> float:
        """X coordinate of the node."""
        return self._node.XCoordinate

    @property
    def ycoord(self) -> float:
        """Y coordinate of the node."""
        return self._node.YCoordinate

    @property
    def ground_level(self) -> float | None:
        """Ground level of the node.

        Returns
        -------
            float: Ground level of the node.
            None: If the node does not have a ground level.
        """
        if hasattr(self._node, "GroundLevel"):
            return self._node.GroundLevel
        return None

    @property
    def bottom_level(self) -> float | None:
        """Bottom level of the node.

        Returns
        -------
            float: Bottom level of the node.
            None: If the node does not have a bottom level.
        """
        if hasattr(self._node, "BottomLevel"):
            return self._node.BottomLevel
        return None

    @property
    def critical_level(self) -> float | None:
        """Critical level of the node.

        Returns
        -------
            float: Critical level of the node.
            None: If the node does not have a critical level.
        """
        if hasattr(self._node, "CriticalLevel"):
            return self._node.CriticalLevel
        return None

    @property
    def diameter(self) -> float | None:
        """Diameter of the node.

        Returns
        -------
            float: Diameter of the node.
            None: If the node does not have a diameter.
        """
        if hasattr(self._node, "Diameter"):
            return self._node.Diameter
        return None
