from ..dotnet import pythonnet_implementation as impl
from .result_locations import ResultLocations
from .result_structure import ResultStructure
from .various import make_proper_variable_name


class ResultStructures(ResultLocations):
    """
    Class for wrapping ResultData structure data items.

    By itself it is also a dict, which contains
    mapping between structure ID and a ResultStructure object.

    Parameters
    ----------
    res1d : Res1D
        Res1D object the structure data items belong to.

    Attributes
    ----------
    structure_label : str
        A label, which is appended if the structure ID starts
        with a number. The value used is structure_label = 's_'
    result_structure_map : dict
        Dictionary from structure ID to a ResultStructure object.
    """

    def __init__(self, res1d):
        ResultLocations.__init__(self, res1d)
        self.structure_label = 's_'
        self.result_structure_map = { }

        res1d.result_network.structures = self
        self.set_structures()
        self.set_quantity_collections()

    def set_structures(self):
        """
        Set attributes to the current ResultReaches object based
        on the reach name.
        """
        for reach in self.data.Reaches:
            for data_item in reach.DataItems:
                # Data items on reaches with defined ItemId
                # correspond to structure data items.
                structure_id = data_item.ItemId
                if structure_id is None:
                    continue

                result_structure = self.get_or_create_result_structure(reach, data_item)
                result_structure_attribute_string = make_proper_variable_name(structure_id, self.structure_label)
                setattr(self, result_structure_attribute_string, result_structure)

    def get_or_create_result_structure(self, reach, data_item):
        """
        Create or get already existing ResultReach object.
        There potentially could be just a single ResultReach object,
        for many IRes1DReach object, which have the same name.

        Also update a result_reach_map dict entry from reach name
        to a list of ResultReach objects.
        """
        structure_id = data_item.ItemId

        result_structure_map = self.result_structure_map
        if structure_id in result_structure_map:
            result_structure = result_structure_map[structure_id]
            result_structure.add_res1d_structure_data_item(data_item)
            return result_structure

        result_structure = ResultStructure(reach, [data_item], self.res1d)
        self.set_res1d_structure_data_item_to_dict(result_structure, data_item)
        result_structure_map[structure_id] = result_structure
        return result_structure

    def set_res1d_structure_data_item_to_dict(self, result_structure, data_item):
        """
        Create a dict entry from reach name to IRes1DReach object
        or a list of IRes1DReach objects.
        """
        structure_id = data_item.ItemId
        self.set_res1d_object_to_dict(structure_id, result_structure)
