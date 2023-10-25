from ..query import QueryDataReach
from .result_location import ResultLocation


class ResultGridPoint(ResultLocation):
    """
    Class for wrapping a single ResultData grid point.

    Parameters
    ----------
    reach: IRes1DReach
        MIKE 1D IRes1DReach object.
    gridpoint IRes1DGridPoint
        MIKE 1D IRes1DGridPoint object.
    data_items : list of IDataItem objects
        A list of IDataItem objects (vector data object) the
        gridpoint has values defined on.
    res1d : Res1D
        Res1D object the grid point belongs to.

    Attributes
    ----------
    structure_data_items : list of IDataItem object.
        List of IDataItem objects belonging to a structures
        defined on the current grid point.
    """

    def __init__(self, reach, gridpoint, data_items, result_reach, res1d):
        empty_data_item_list = []
        ResultLocation.__init__(self, empty_data_item_list, res1d)
        self.reach = reach
        self.gridpoint = gridpoint
        self.result_reach = result_reach
        self.structure_data_items = []
        self.element_indices = []

    def add_to_result_quantity_maps(self, quantity_id, result_quantity):
        """Add grid point result quantity to result quantity maps."""
        self.add_to_result_quantity_map(quantity_id, result_quantity, self.result_quantity_map)

        reach_result_quantity_map = self.result_reach.result_quantity_map
        self.add_to_result_quantity_map(quantity_id, result_quantity, reach_result_quantity_map)

        reaches_result_quantity_map = self.res1d.result_network.reaches.result_quantity_map
        self.add_to_result_quantity_map(quantity_id, result_quantity, reaches_result_quantity_map)

        query = QueryDataReach(quantity_id, self.reach.Name, self.gridpoint.Chainage)
        self.add_to_network_result_quantity_map(query, result_quantity)

    def get_query(self, data_item):
        """Get a QueryDataReach for given data item."""
        quantity_id = data_item.Quantity.Id
        reach_name = self.reach.Name
        chainage = self.gridpoint.Chainage
        query = QueryDataReach(quantity_id, reach_name, chainage)
        return query

    def add_data_item(self, data_item, element_index):
        """Adds data item to grid point data items list."""
        self.data_items.append(data_item)
        self.element_indices.append(element_index)

    def add_structure_data_item(self, data_item):
        """Adds data item to structure data items list."""
        self.structure_data_items.append(data_item)
