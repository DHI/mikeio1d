"""Module for ResultStructure class."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from DHI.Mike1D.ResultDataAccess import IRes1DReach

from warnings import warn

from ..dotnet import pythonnet_implementation as impl
from ..query import QueryDataStructure
from ..quantities import TimeSeriesIdGroup

from .result_location import ResultLocation
from .result_location import ResultLocationCreator


class ResultStructure(ResultLocation):
    """Class for wrapping a list of ResultData structure data items belonging to the same structure.

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
        ResultLocation.__init__(self)

        self._group = TimeSeriesIdGroup.STRUCTURE
        self._name = structure_id
        self._tag = reach.Name
        self._id = structure_id
        self._chainage = None

        self._creator = ResultStructureCreator(self, reach, data_items, res1d)
        self._creator.create()

    def __repr__(self) -> str:
        """Return a string representation of ResultStructure."""
        return f"<{self.type}: {self.id}>"

    @property
    def reach(self) -> IRes1DReach:
        """IRes1DReach corresponding to this result structure."""
        # TODO: Consider to remove or rename this property to res1d_reach for version 1.0.0
        return self._creator.reach

    @property
    def structure_id(self):
        """Get structure ID."""
        # TODO: Remove this in 1.0.0
        warn(
            "Please use .id instead of .structure_id. This attribute will be removed in the future."
        )
        return self.id

    def get_m1d_dataset(self, m1d_dataitem=None):
        """Get IRes1DDataSet object associated with ResultStructure.

        This is the reach IRes1DDataSet object because ResultStructure objects do not
        have a corresonding IRes1DDataSet object.

        Parameters
        ----------
        m1d_dataitem: IDataItem, optional
            Ignored for ResultStructure.

        Returns
        -------
        IRes1DDataSet
            IRes1DDataSet object associated with ResultStructure.

        """
        return self.reach

    def get_query(self, data_item):
        """Get a QueryDataStructure for given data item."""
        quantity_id = data_item.Quantity.Id
        structure_id = self.id
        query = QueryDataStructure(quantity_id, structure_id, self.reach.Name, self._chainage)
        return query

    @property
    def id(self) -> str:
        """Structure ID."""
        return self._id

    @property
    def type(self) -> str:
        """Type of the structure."""
        return self.reach.Name.split(":")[0]

    @property
    def chainage(self) -> float:
        """Chainage of the structure."""
        return self._chainage


class ResultStructureCreator(ResultLocationCreator):
    """Helper class for creating ResultGridPoint.

    Parameters
    ----------
    result_location : ResultGridPoint
        Instance of ResultGridPoint, which the ResultGridPointCreator deals with.
    reach: IRes1DReach
        MIKE 1D IRes1DReach object.
    gridpoint IRes1DGridPoint
        MIKE 1D IRes1DGridPoint object.
    data_items : list of IDataItem objects
        A list of IDataItem objects (vector data object) the
        gridpoint has values defined on.
    result_reach : ResultReach
        Instance of ResultReach that this ResultGridPoint belongs to.
    res1d : Res1D
        Res1D object the grid point belongs to.

    Attributes
    ----------
    structure_data_items : list of IDataItem object.
        List of IDataItem objects belonging to a structures
        defined on the current grid point.

    """

    def __init__(self, result_location, reach, data_items, res1d):
        empty_data_item_list = []
        ResultLocationCreator.__init__(self, result_location, empty_data_item_list, res1d)

        self.data_items_intial = data_items
        self.reach = reach
        self.data_items_dict = {}

    def create(self):
        """Perform ResultGridPoint creation steps."""
        for data_item in self.data_items_intial:
            self.add_res1d_structure_data_item(data_item)

        self.set_static_attributes()

    def set_static_attributes(self):
        """Set static attributes. These show up in the html repr."""
        self.set_static_attribute("id")
        self.set_static_attribute("type")
        self.set_static_attribute("chainage")

    def add_to_result_quantity_maps(self, quantity_id, result_quantity):
        """Add structure result quantity to result quantity maps."""
        self.add_to_result_quantity_map(quantity_id, result_quantity, self.result_quantity_map)

        structure_result_quantity_map = self.res1d.network.structures._creator.result_quantity_map
        self.add_to_result_quantity_map(quantity_id, result_quantity, structure_result_quantity_map)

        self.add_to_network_result_quantity_map(result_quantity)

    def add_res1d_structure_data_item(self, data_item):
        """Add a IDataItem to ResultStructure.

        Parameters
        ----------
        data_item: IDataItem
            A MIKE 1D IDataItem object.

        """
        if self.result_location._chainage is None:
            index_list = list(data_item.IndexList)
            gridpoint_index = index_list[0]
            gridpoints = list(self.reach.GridPoints)
            self.result_location._chainage = gridpoints[gridpoint_index].Chainage

        self.data_items.append(data_item)
        self.data_items_dict[data_item.Quantity.Id] = data_item
        self.set_quantity(self.result_location, data_item)

    @staticmethod
    def get_structure_id(reach, data_item):
        """Get structure ID either from IDataItem.ItemId or for structure reaches from actual Res1DStructureGridPoint structure."""
        if data_item.ItemId is not None:
            return data_item.ItemId

        if reach.IsStructureReach:
            structure_gridpoint = impl(list(reach.GridPoints)[1])
            structures = list(structure_gridpoint.Structures)
            structure_id = structures[0].Id
            return structure_id

        return None

    def get_data_item(self, quantity_id):
        """Retrieve a data item for given quantity id."""
        return self.data_items_dict[quantity_id]
