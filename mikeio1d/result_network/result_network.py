from .result_nodes import ResultNodes
from .result_reaches import ResultReaches
from .result_catchments import ResultCatchments
from .result_global_datas import ResultGlobalDatas
from .result_structures import ResultStructures


class ResultNetwork:
    """
    Class for storing ResultData network wrapper.

    This class is mainly used to provide for network
    location attributes, which can then be accessed
    in an IDE using auto-completion.

    Parameters
    ----------
    res1d : Res1D
        Res1D object the network belongs to.

    Attributes
    ----------
    data : ResultData
        MIKE 1D ResultData object.
    data_items : IDataItems.
        MIKE 1D IDataItems object.
    queries_ids : set
        A set of string representing query ids, i.e., query.__repr__()
    queries : list of QueryData objects
        A list of actual QueryData object, which are used when res1d.read() is called.
    nodes : ResultNodes object
        Is is a wrapper class object for all ResultData nodes.
    reaches : ResultReaches object
        Is a wrapper class object for all ResultData reaches.
    catchments : ResultCatchments object
        Is a wrapper class object for all ResultData catchments.
    global_data : ResultGlobalDatas object
        Is a wrapper class object for all ResultData global data items.
    result_quantity_map : dict
        Dictionary from unique query label to a ResultQuantity object corresponding
        to that query. The keys of this dictionary should represent all possible query labels.

    Examples
    --------
    An example of adding a query for some location using ResultNetwork
    for nodes with ID 'node1', 'node2' and reaches with ID 'reach1', 'reach2'
    and chainage equal 0, for WaterLevel quantity:
    ```python
    >>> res1d = Res1D('MyRes1D.res1d')
    >>> resnet = ResultNetwork(res1d)
    >>> resnet.nodes.node1.WaterLevel.add()
    >>> resnet.nodes.node2.WaterLevel.add()
    >>> resnet.reaches.reach1.m_0_0.WaterLevel.add()
    >>> resnet.reaches.reach2.m_0_0.WaterLevel.add()
    ```
    """

    def __init__(self, res1d):
        self.res1d = res1d
        self.data = res1d.data
        self.data_items = res1d.data.DataItems

        self.queries_ids = set()
        self.queries = []

        self.result_quantity_map = {}

        self.res1d.result_network = self
        self.set_result_locations()

    def set_result_locations(self):
        """
        Assign nodes, reaches, catchments, global_data properties.
        """
        res1d = self.res1d
        self.nodes = ResultNodes(res1d)
        self.reaches = ResultReaches(res1d)
        self.catchments = ResultCatchments(res1d)
        self.structures = ResultStructures(res1d)
        self.global_data = ResultGlobalDatas(res1d)

    def add_query(self, query):
        """
        Add a query to the queries list, which can be used
        when calling res1D.read().
        """
        query_string = query.__repr__()
        queries = self.queries
        queries_ids = self.queries_ids
        if query_string not in queries_ids:
            queries_ids.add(query_string)
            queries.append(query)

    def convert_queries_to_data_entries(self, queries):
        data_entries = []

        for query in queries:
            query_label = str(query)
            result_quantity = self.result_quantity_map[query_label]
            data_entry = result_quantity.get_data_entry()
            data_entries.append(data_entry)

        return data_entries
