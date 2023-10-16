from ..query import QueryDataNode
from .result_location import ResultLocation


class ResultNode(ResultLocation):
    """
    Class for wrapping a single ResultData node.

    Parameters
    ----------
    node: IRes1DNode
        MIKE 1D IRes1DNode object.
    res1d : Res1D
        Res1D object the node belongs to.
    """

    def __init__(self, node, res1d):
        ResultLocation.__init__(self, node.DataItems, res1d)
        self.node = node
        self.set_quantities()
        self.set_static_attributes()

    def set_static_attributes(self):
        """Set static attributes. These show up in the html repr."""
        self._static_attributes = []

        node_type = self.node.GetType().Name[5:]  # Removes 'Res1D' from type name
        self.set_static_attribute("type", node_type)
        self.set_static_attribute("id", self.node.Id)
        self.set_static_attribute("xcoord", self.node.XCoordinate)
        self.set_static_attribute("ycoord", self.node.YCoordinate)

        # Collect attributes depending on node type
        if self.type in ["Basin", "Manhole", "SewerJunction"]:
            self.set_static_attribute("ground_level", self.node.GroundLevel)
            self.set_static_attribute("bottom_level", self.node.BottomLevel)
            self.set_static_attribute("critical_level", self.node.CriticalLevel)
        if self.type == "Manhole":
            self.set_static_attribute("diameter", self.node.Diameter)

    def add_to_result_quantity_maps(self, quantity_id, result_quantity):
        """Add node result quantity to result quantity maps."""
        self.add_to_result_quantity_map(
            quantity_id, result_quantity, self.result_quantity_map
        )

        nodes_result_quantity_map = self.res1d.result_network.nodes.result_quantity_map
        self.add_to_result_quantity_map(
            quantity_id, result_quantity, nodes_result_quantity_map
        )

        query = QueryDataNode(quantity_id, self.node.ID, validate=False)
        self.add_to_network_result_quantity_map(query, result_quantity)

    def get_query(self, data_item):
        """Get a QueryDataNode for given data item."""
        quantity_id = data_item.Quantity.Id
        node_id = self.node.ID
        query = QueryDataNode(quantity_id, node_id)
        return query
