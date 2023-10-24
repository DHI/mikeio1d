from warnings import warn

from ..query import QueryDataNode
from .result_location import ResultLocation


class ResultNode(ResultLocation):
    """
    Class for wrapping a single ResultData node.

    Parameters
    ----------
    res1d : Res1D
        Res1D object the node belongs to.
    """

    def __init__(self, node, res1d):
        ResultLocation.__init__(self, node.DataItems, res1d)
        self._node = node
        self.set_quantities()
        self.set_static_attributes()

    def __repr__(self) -> str:
        return f"<{self.type}: {self.id}>"

    def __getattr__(self, name: str):
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

    def set_static_attributes(self):
        """Set static attributes. These show up in the html repr."""
        self._static_attributes = []

        node_type = self._node.GetType().Name[5:]  # Removes 'Res1D' from type name
        self.set_static_attribute("id", self._node.Id)
        self.set_static_attribute("type", node_type)
        self.set_static_attribute("xcoord", self._node.XCoordinate)
        self.set_static_attribute("ycoord", self._node.YCoordinate)

        # Collect attributes depending on node type
        if self.type in ["Basin", "Manhole", "SewerJunction"]:
            self.set_static_attribute("ground_level", self._node.GroundLevel)
            self.set_static_attribute("bottom_level", self._node.BottomLevel)
            self.set_static_attribute("critical_level", self._node.CriticalLevel)
        if self.type == "Manhole":
            self.set_static_attribute("diameter", self._node.Diameter)

    def add_to_result_quantity_maps(self, quantity_id, result_quantity):
        """Add node result quantity to result quantity maps."""
        self.add_to_result_quantity_map(
            quantity_id, result_quantity, self.result_quantity_map
        )

        nodes_result_quantity_map = self.res1d.result_network.nodes.result_quantity_map
        self.add_to_result_quantity_map(
            quantity_id, result_quantity, nodes_result_quantity_map
        )

        query = QueryDataNode(quantity_id, self._node.ID, validate=False)
        self.add_to_network_result_quantity_map(query, result_quantity)

    def get_query(self, data_item):
        """Get a QueryDataNode for given data item."""
        quantity_id = data_item.Quantity.Id
        node_id = self._node.ID
        query = QueryDataNode(quantity_id, node_id)
        return query
