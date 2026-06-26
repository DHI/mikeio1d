"""ResultCatchment class."""

from __future__ import annotations
from warnings import warn
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from ..res1d import Res1D
    from ..geometry import CatchmentGeometry
    from .result_quantity import ResultQuantity

    from DHI.Mike1D.ResultDataAccess import IDataItem
    from DHI.Mike1D.ResultDataAccess import IRes1DCatchment

from ..query import QueryDataCatchment
from ..various import try_import_shapely
from ..quantities import TimeSeriesIdGroup

from .result_location import ResultLocation
from .result_location import ResultLocationCreator


class ResultCatchment(ResultLocation):
    """Class for wrapping a single ResultData catchment.

    Parameters
    ----------
    catchment: IRes1DCatchment
        MIKE 1D IRes1DCatchment object.
    res1d : Res1D
        Res1D object the catchment belongs to.
    """

    def __init__(self, catchment: IRes1DCatchment, res1d: Res1D):
        ResultLocation.__init__(self)

        self._group = TimeSeriesIdGroup.CATCHMENT
        self._name = catchment.Id

        self._creator = ResultCatchmentCreator(self, catchment, res1d)
        self._creator.create()

    def __repr__(self) -> str:
        """Return a string representation of the ResultCatchment object."""
        return f"<Catchment: {self.id}>"

    @property
    def res1d_catchment(self) -> IRes1DCatchment:
        """DHI.Mike1D.ResultDataAccess.IRes1DCatchment corresponding to this result location."""
        return self._creator.catchment

    @property
    def id(self) -> str:
        """The ID of the catchment."""
        return self.res1d_catchment.Id

    @property
    def area(self) -> float:
        """The area of the catchment."""
        return self.res1d_catchment.Area

    @property
    def type(self) -> str:
        """The type of the catchment."""
        return self.res1d_catchment.Type

    @property
    def geometry(self) -> CatchmentGeometry:
        """A geometric representation of the catchment. Requires shapely."""
        try_import_shapely()
        from ..geometry import CatchmentGeometry

        return CatchmentGeometry.from_res1d_catchment(self.res1d_catchment)

    def get_m1d_dataset(self, m1d_dataitem: IDataItem = None) -> IRes1DCatchment:
        """Get IRes1DDataSet object associated with ResultCatchment.

        Parameters
        ----------
        m1d_dataitem: IDataItem, optional
            Ignored for ResultCatchment.

        Returns
        -------
        IRes1DDataSet
            IRes1DDataSet object associated with ResultCatchment.

        """
        return self.res1d_catchment

    def get_query(self, data_item: IDataItem) -> QueryDataCatchment:
        """Get a QueryDataCatchment for given data item."""
        quantity_id = data_item.Quantity.Id
        catchment_id = self.res1d_catchment.Id
        query = QueryDataCatchment(quantity_id, catchment_id)
        return query


class ResultCatchmentCreator(ResultLocationCreator):
    """Helper class for creating ResultCatchment.

    Parameters
    ----------
    result_location:
        Instance of ResultCatchment, which the ResultCatchmentCreator deals with.
    catchment: IRes1DCatchment
        MIKE 1D IRes1DCatchment object.
    res1d : Res1D
        Res1D object the catchment belongs to.

    """

    def __init__(
        self,
        result_location: ResultCatchment,
        catchment: IRes1DCatchment,
        res1d: Res1D,
    ):
        ResultLocationCreator.__init__(self, result_location, catchment.DataItems, res1d)
        self.catchment: IRes1DCatchment = catchment

    def create(self):
        """Perform ResultCatchment creation steps."""
        self.set_quantities()
        self.set_static_attributes()

    def set_static_attributes(self):
        """Set static attributes. These show up in the html repr."""
        self.set_static_attribute("id")
        self.set_static_attribute("area")
        self.set_static_attribute("type")

    def add_to_result_quantity_maps(self, quantity_id: str, result_quantity: ResultQuantity):
        """Add catchment result quantity to result quantity maps."""
        self.add_to_result_quantity_map(quantity_id, result_quantity, self.result_quantity_map)

        catchment_result_quantity_map = self.res1d.network.catchments._creator.result_quantity_map
        self.add_to_result_quantity_map(quantity_id, result_quantity, catchment_result_quantity_map)

        self.add_to_network_result_quantity_map(result_quantity)
