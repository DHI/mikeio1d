from ..dotnet import pythonnet_implementation as impl
from ..query import QueryDataStructure
from .result_location import ResultLocation


class ResultStructure(ResultLocation):
    """
    Class for wrapping a list of ResultData structure data items
    belonging to the same structure.

    Parameters
    ----------
    structure_id : str
        Structure ID.
    reach: IRes1DReach
        Reach where the structure belongs to.
    res1d : Res1D
        Res1D object the reach belongs to.

    Attributes
    ----------
    data_items : list of IDataItems objects.
        A list of MIKE 1D IDataItems objects corresponding to a given structure.
    data_items_dict : dict
        A dictionary from quantity id to a data item.
    chainage : float
        Chainage where the structure is located on the reach.
    """

    def __init__(self, structure_id, reach, data_items, res1d):
        empty_list = []
        ResultLocation.__init__(self, empty_list, res1d)

        self.structure_id = structure_id
        self.reach = reach
        self.chainage = None

        self.data_items_dict = {}
        for data_item in data_items:
            self.add_res1d_structure_data_item(data_item)

    def add_to_result_quantity_maps(self, quantity_id, result_quantity):
        """ Add structure result quantity to result quantity maps. """
        self.add_to_result_quantity_map(quantity_id, result_quantity, self.result_quantity_map)

        structure_result_quantity_map = self.res1d.result_network.structures.result_quantity_map
        self.add_to_result_quantity_map(quantity_id, result_quantity, structure_result_quantity_map)

        query = QueryDataStructure(quantity_id, self.structure_id, self.reach.Name, self.chainage)
        self.add_to_network_result_quantity_map(query, result_quantity)

    def add_res1d_structure_data_item(self, data_item):
        """
        Add a IDataItem to ResultStructure.

        Parameters
        ----------
        data_item: IDataItem
            A MIKE 1D IDataItem object.
        """
        if self.chainage is None:
            index_list = list(data_item.IndexList)
            gridpoint_index = index_list[0]
            gridpoints = list(self.reach.GridPoints)
            self.chainage = gridpoints[gridpoint_index].Chainage

        self.data_items.append(data_item)
        self.data_items_dict[data_item.Quantity.Id] = data_item
        self.set_quantity(self, data_item)

    @staticmethod
    def get_structure_id(reach, data_item):
        """
        Gets structure ID either from IDataItem.ItemId or for structure reaches
        from actual Res1DStructureGridPoint structure.
        """
        if data_item.ItemId is not None:
            return data_item.ItemId

        if reach.IsStructureReach:
            structure_gridpoint = impl(list(reach.GridPoints)[1])
            structures = list(structure_gridpoint.Structures)
            structure_id = structures[0].Id
            return structure_id

        return None

    def get_data_item(self, quantity_id):
        """ Retrieve a data item for given quantity id. """
        return self.data_items_dict[quantity_id]

    def add_query(self, data_item):
        """ Add QueryDataStructure to ResultNetwork.queries list."""
        quantity_id = data_item.Quantity.Id
        structure_id = self.structure_id
        query = QueryDataStructure(quantity_id, structure_id, self.reach.Name, self.chainage)
        self.res1d.result_network.add_query(query)
