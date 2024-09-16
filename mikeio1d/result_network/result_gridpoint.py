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

        self.set_static_attributes()

    def set_static_attributes(self):
        """Set static attributes. These show up in the html repr."""
        self.set_static_attribute("reach_name", self.reach.Name)
        self.set_static_attribute("chainage", self.gridpoint.Chainage)
        self.set_static_attribute("xcoord", self.gridpoint.X)
        self.set_static_attribute("ycoord", self.gridpoint.Y)
        self.set_static_attribute("bottom_level", self.gridpoint.Z)

    def get_m1d_dataset(self, m1d_dataitem=None):
        """Get IRes1DDataSet object associated with ResultGridPoint.

        This is the reach IRes1DDataSet object because grid points do not
        have a corresponding IRes1DDataSet object.

        Parameters
        ----------
        m1d_dataitem: IDataItem, optional
            Ignored for ResultGridPoint.

        Returns
        -------
        IRes1DDataSet
            IRes1DDataSet object associated with ResultGridPoint."""

        return self.reach

    def add_to_result_quantity_maps(self, quantity_id, result_quantity):
        """Add grid point result quantity to result quantity maps."""
        self.add_to_result_quantity_map(quantity_id, result_quantity, self.result_quantity_map)

        reach_result_quantity_map = self.result_reach.result_quantity_map
        self.add_to_result_quantity_map(quantity_id, result_quantity, reach_result_quantity_map)

        reaches_result_quantity_map = self.res1d.result_network.reaches.result_quantity_map
        self.add_to_result_quantity_map(quantity_id, result_quantity, reaches_result_quantity_map)

        self.add_to_network_result_quantity_map(result_quantity)

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
