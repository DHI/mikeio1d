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

    def add_to_result_quantity_maps(self, quantity_id, result_quantity):
        """ Add node result quantity to result quantity maps. """
        self.add_to_result_quantity_map(quantity_id, result_quantity, self.result_quantity_map)

        nodes_result_quantity_map = self.res1d.result_network.nodes.result_quantity_map
        self.add_to_result_quantity_map(quantity_id, result_quantity, nodes_result_quantity_map)

        query = QueryDataNode(quantity_id, self.node.ID, validate=False)
        self.add_to_network_result_quantity_map(query, result_quantity)

    def add_query(self, data_item):
        """ Add QueryDataNode to ResultNetwork.queries list."""
        quantity_id = data_item.Quantity.Id
        node_id = self.node.ID
        query = QueryDataNode(quantity_id, node_id)
        self.res1d.result_network.add_query(query)
