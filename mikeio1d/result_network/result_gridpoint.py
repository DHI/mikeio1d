"""ResultGridPoint class."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from typing import List

    from ..res1d import Res1D
    from .result_reach import ResultReach

    from DHI.Mike1D.ResultDataAccess import IDataItem
    from DHI.Mike1D.ResultDataAccess import IDataItems
    from DHI.Mike1D.ResultDataAccess import IRes1DReach
    from DHI.Mike1D.ResultDataAccess import IRes1DGridPoint

from ..query import QueryDataReach
from ..quantities import TimeSeriesIdGroup

from .result_location import ResultLocation
from .result_location import ResultLocationCreator


class ResultGridPoint(ResultLocation):
    """Class for wrapping a single ResultData grid point.

    Parameters
    ----------
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
    tag : str
        Tag for reach location span where grid point belongs to.

    """

    def __init__(
        self,
        reach: IRes1DReach,
        gridpoint: IRes1DGridPoint,
        data_items: IDataItems,
        result_reach: ResultReach,
        res1d: Res1D,
        tag: str = "",
    ):
        ResultLocation.__init__(self)

        self._group = TimeSeriesIdGroup.REACH
        self._name = reach.Name
        self._chainage = gridpoint.Chainage
        self._tag = tag

        self._creator = ResultGridPointCreator(
            self, reach, gridpoint, data_items, result_reach, res1d
        )
        self._creator.create()

    @property
    def reach(self) -> ResultReach:
        """Instance of ResultReach that this ResultGridPoint belongs to."""
        return self._creator.result_reach

    @property
    def res1d_reach(self) -> IRes1DReach:
        """DHI.Mike1D.ResultDataAccess.IRes1DReach corresponding to this result location."""
        return self._creator.reach

    @property
    def res1d_gridpoint(self) -> IRes1DGridPoint:
        """DHI.Mike1D.ResultDataAccess.IRes1DGridPoint corresponding to this result location."""
        return self._creator.gridpoint

    @property
    def reach_name(self):
        """Name of reach the gridpoint is on."""
        return self._creator.reach.Name

    @property
    def chainage(self):
        """Chainage of the gridpoint."""
        return self.res1d_gridpoint.Chainage

    @property
    def xcoord(self):
        """X coordinate of the gridpoint."""
        return self.res1d_gridpoint.X

    @property
    def ycoord(self):
        """Y coordinate of the gridpoint."""
        return self.res1d_gridpoint.Y

    @property
    def bottom_level(self):
        """Bottom level of the gridpoint."""
        return self.res1d_gridpoint.Z

    def get_m1d_dataset(self, m1d_dataitem: IDataItem = None) -> IRes1DGridPoint:
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
            IRes1DDataSet object associated with ResultGridPoint.

        """
        return self.res1d_reach

    def get_query(self, data_item: IDataItem) -> QueryDataReach:
        """Get a QueryDataReach for given data item."""
        quantity_id = data_item.Quantity.Id
        reach_name = self.reach.Name
        chainage = self.res1d_gridpoint.Chainage
        query = QueryDataReach(quantity_id, reach_name, chainage)
        return query

    # region Deprecated methods and attributes of ResultReach.

    @property
    def result_reach(self) -> ResultReach:
        """Instance of ResultReach that this ResultGridPoint belongs to."""
        return self.reach

    @property
    def gridpoint(self) -> IRes1DGridPoint:
        """IRes1DGridPoint corresponding to this result location."""
        return self._creator.gridpoint

    # endregion


class ResultGridPointCreator(ResultLocationCreator):
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

    def __init__(
        self,
        result_location: ResultGridPoint,
        reach: IRes1DReach,
        gridpoint: IRes1DGridPoint,
        data_items: IDataItems,
        result_reach: ResultReach,
        res1d: Res1D,
    ):
        empty_data_item_list: List[IDataItem] = []
        ResultLocationCreator.__init__(self, result_location, empty_data_item_list, res1d)

        self.reach = reach
        self.gridpoint = gridpoint
        self.result_reach = result_reach
        self.structure_data_items = []
        self.element_indices = []

    def create(self):
        """Perform ResultGridPoint creation steps."""
        self.set_static_attributes()

    def set_static_attributes(self):
        """Set static attributes. These show up in the html repr."""
        self.set_static_attribute("reach_name")
        self.set_static_attribute("chainage")
        self.set_static_attribute("xcoord")
        self.set_static_attribute("ycoord")
        self.set_static_attribute("bottom_level")

    def add_to_result_quantity_maps(self, quantity_id, result_quantity):
        """Add grid point result quantity to result quantity maps."""
        self.add_to_result_quantity_map(quantity_id, result_quantity, self.result_quantity_map)

        reach_result_quantity_map = self.result_reach._creator.result_quantity_map
        self.add_to_result_quantity_map(quantity_id, result_quantity, reach_result_quantity_map)

        reaches_result_quantity_map = self.res1d.network.reaches._creator.result_quantity_map
        self.add_to_result_quantity_map(quantity_id, result_quantity, reaches_result_quantity_map)

        self.add_to_network_result_quantity_map(result_quantity)

    def add_data_item(self, data_item, element_index):
        """Add data item to grid point data items list."""
        self.data_items.append(data_item)
        self.element_indices.append(element_index)

    def add_structure_data_item(self, data_item):
        """Add data item to structure data items list."""
        self.structure_data_items.append(data_item)
