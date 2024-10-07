from .result_locations import ResultLocations
from .result_structure import ResultStructure
from .various import make_proper_variable_name
from ..quantities import TimeSeriesIdGroup


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
        self._group = TimeSeriesIdGroup.STRUCTURE
        self.structure_label = "s_"
        self.result_structure_map = {}

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
                if not self.is_structure(reach, data_item):
                    continue

                result_structure = self.get_or_create_result_structure(reach, data_item)
                structure_id = result_structure.id
                result_structure_attribute_string = make_proper_variable_name(
                    structure_id, self.structure_label
                )
                setattr(self, result_structure_attribute_string, result_structure)

    def is_structure(self, reach, data_item):
        # Data items on reaches with defined ItemId correspond to structure data items.
        if data_item.ItemId is not None:
            return True

        # Data item with no index list is not a structure data item.
        if data_item.IndexList is None:
            return False

        is_data_item_for_single_grid_point = len(list(data_item.IndexList)) == 1
        has_three_grid_points = len(list(reach.GridPoints)) == 3

        if (
            reach.IsStructureReach
            and has_three_grid_points
            and is_data_item_for_single_grid_point
        ):
            return True

        return False

    def get_or_create_result_structure(self, reach, data_item):
        """
        Create or get already existing ResultStructure object.

        Also update a result_structure_map dict entry from structure ID
        to a ResultStructure object.
        """
        structure_id = ResultStructure.get_structure_id(reach, data_item)

        result_structure_map = self.result_structure_map
        if structure_id in result_structure_map:
            result_structure = result_structure_map[structure_id]
            result_structure.add_res1d_structure_data_item(data_item)
            return result_structure

        result_structure = ResultStructure(structure_id, reach, [data_item], self.res1d)
        self.set_res1d_object_to_dict(structure_id, result_structure)
        result_structure_map[structure_id] = result_structure
        return result_structure
