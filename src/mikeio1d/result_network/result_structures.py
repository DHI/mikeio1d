"""Module for ResultStructures class."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from typing import List
    from typing import Dict

    from ..res1d import Res1D
    from .result_quantity import ResultQuantity

    from DHI.Mike1D.ResultDataAccess import IDataItem
    from DHI.Mike1D.ResultDataAccess import IRes1DReach

from ..quantities import TimeSeriesIdGroup

from .result_locations import ResultLocations
from .result_locations import ResultLocationsCreator
from .result_structure import ResultStructure
from .result_structure import ResultStructureCreator
from .various import make_proper_variable_name


class ResultStructures(ResultLocations):
    """Class for wrapping ResultData structure data items.

    By itself it is also a dict, which contains
    mapping between structure ID and a ResultStructure object.

    Parameters
    ----------
    res1d : Res1D
        Res1D object the structure data items belong to.

    """

    def __init__(self, res1d: Res1D):
        ResultLocations.__init__(self)

        res1d.network.structures = self
        self._group = TimeSeriesIdGroup.STRUCTURE

        self._creator = ResultStructuresCreator(self, res1d)
        self._creator.create()


class ResultStructuresCreator(ResultLocationsCreator):
    """A helper class for creating ResultStructures.

    Parameters
    ----------
    result_locations : ResultStructures
        Instance of ResultStructures, which the ResultStructuresCreator deals with.
    res1d : Res1D
        Res1D object the structures belong to.

    Attributes
    ----------
    structure_label : str
        A label, which is appended if the structure ID starts
        with a number. The value used is structure_label = 's_'
    result_structure_map : dict
        Dictionary from structure ID to a ResultStructure object.

    """

    def __init__(self, result_locations: ResultStructures, res1d: Res1D):
        ResultLocationsCreator.__init__(self, result_locations, res1d)
        self.structure_label = "s_"
        self.result_structure_map: Dict[str, ResultStructure] = {}

    def create(self):
        """Perform ResultStructures creation steps."""
        self.set_structures()
        self.set_quantity_collections()

    def set_structures(self):
        """Set attributes to the current ResultReaches object based on the reach name."""
        for reach in self.data.Reaches:
            if not self.res1d.reader.is_data_set_included(reach):
                continue

            for data_item in reach.DataItems:
                if not self.is_structure(reach, data_item):
                    continue

                result_structure = self.get_or_create_result_structure(reach, data_item)
                structure_id = result_structure.id
                result_structure_attribute_string = make_proper_variable_name(
                    structure_id, self.structure_label
                )
                setattr(self.result_locations, result_structure_attribute_string, result_structure)

    def is_structure(self, reach: IRes1DReach, data_item: IDataItem) -> bool:
        """Check if a data item is a structure data item."""
        # Data items on reaches with defined ItemId correspond to structure data items.
        if data_item.ItemId is not None:
            return True

        # Data item with no index list is not a structure data item.
        if data_item.IndexList is None:
            return False

        is_data_item_for_single_grid_point = len(list(data_item.IndexList)) == 1
        has_three_grid_points = len(list(reach.GridPoints)) == 3

        if reach.IsStructureReach and has_three_grid_points and is_data_item_for_single_grid_point:
            return True

        return False

    def get_or_create_result_structure(
        self, reach: IRes1DReach, data_item: IDataItem
    ) -> ResultStructure:
        """Create or get already existing ResultStructure object.

        Also update a result_structure_map dict entry from structure ID
        to a ResultStructure object.
        """
        structure_id = ResultStructureCreator.get_structure_id(reach, data_item)

        result_structure_map = self.result_structure_map
        if structure_id in result_structure_map:
            result_structure = result_structure_map[structure_id]
            result_structure._creator.add_res1d_structure_data_item(data_item)
            return result_structure

        result_structure = ResultStructure(structure_id, reach, [data_item], self.res1d)
        self.set_res1d_object_to_dict(structure_id, result_structure)
        result_structure_map[structure_id] = result_structure
        return result_structure
