from ..dotnet import pythonnet_implementation as impl
from .result_locations import ResultLocations
from .result_node import ResultNode
from .various import make_proper_variable_name


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
        self.node_label = 'n_'
        self.set_nodes()

    def set_nodes(self):
        """
        Set attributes to the current ResultNodes object based
        on the node ID.
        """
        for node in self.data.Nodes:
            self.set_res1d_node_to_dict(node)
            result_node = ResultNode(node, self.res1d)
            result_node_attribute_string = make_proper_variable_name(node.ID, self.node_label)
            setattr(self, result_node_attribute_string, result_node)

    def set_res1d_node_to_dict(self, node):
        """
        Create a dict entry from node ID to IRes1DNode object.
        """
        node = impl(node)
        self[node.ID] = node
