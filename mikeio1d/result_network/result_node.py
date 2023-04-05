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

    def add_query(self, data_item):
        """ Add QueryDataNode to ResultNetwork.queries list."""
        quantity_id = data_item.Quantity.Id
        node_id = self.node.ID
        query = QueryDataNode(quantity_id, node_id)
        self.res1d.result_network.add_query(query)
