from __future__ import annotations
from warnings import warn
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from ..geometry import CatchmentGeometry

from ..query import QueryDataCatchment
from .result_location import ResultLocation
from ..various import try_import_shapely
from ..quantities import TimeSeriesIdGroup


class ResultCatchment(ResultLocation):
    """
    Class for wrapping a single ResultData catchment.

    Parameters
    ----------
    catchment: IRes1DCatchment
        MIKE 1D IRes1DCatchment object.
    res1d : Res1D
        Res1D object the catchment belongs to.
    """

    def __init__(self, catchment, res1d):
        ResultLocation.__init__(self, catchment.DataItems, res1d)
        self._group = TimeSeriesIdGroup.CATCHMENT
        self._catchment = catchment
        self.set_quantities()
        self.set_static_attributes()

    def __repr__(self) -> str:
        return f"<Catchment: {self.id}>"

    def __getattr__(self, name: str):
        # TODO: Remove this in 1.0.0
        if name == "catchment":
            warn(
                "Accessing IRes1DCatchment attribute via .catchment is deprecated. Use ._catchment."
            )
            return self._catchment

        elif hasattr(self._catchment, name):
            warn(
                f"Accessing IRes1DCatchment attribute {name} directly is deprecated. Use static attributes instead, or ._catchment.{name}."
            )
            return getattr(self._catchment, name)
        else:
            object.__getattribute__(self, name)

    def get_m1d_dataset(self, m1d_dataitem=None):
        """Get IRes1DDataSet object associated with ResultCatchment.

        Parameters
        ----------
        m1d_dataitem: IDataItem, optional
            Ignored for ResultCatchment.

        Returns
        -------
        IRes1DDataSet
            IRes1DDataSet object associated with ResultCatchment."""

        return self._catchment

    def set_static_attributes(self):
        """Set static attributes. These show up in the html repr."""
        self.set_static_attribute("id", self._catchment.Id)
        self.set_static_attribute("area", self._catchment.Area)
        self.set_static_attribute("type", self._catchment.Type)

    def add_to_result_quantity_maps(self, quantity_id, result_quantity):
        """Add catchment result quantity to result quantity maps."""
        self.add_to_result_quantity_map(
            quantity_id, result_quantity, self.result_quantity_map
        )

        catchment_result_quantity_map = (
            self.res1d.result_network.catchments.result_quantity_map
        )
        self.add_to_result_quantity_map(
            quantity_id, result_quantity, catchment_result_quantity_map
        )

        self.add_to_network_result_quantity_map(result_quantity)

    def get_query(self, data_item):
        """Get a QueryDataCatchment for given data item."""
        quantity_id = data_item.Quantity.Id
        catchment_id = self._catchment.Id
        query = QueryDataCatchment(quantity_id, catchment_id)
        return query

    @property
    def geometry(self) -> CatchmentGeometry:
        """
        A geometric representation of the catchment. Requires shapely.
        """
        try_import_shapely()
        from ..geometry import CatchmentGeometry

        return CatchmentGeometry.from_res1d_catchment(self._catchment)
