"""Module for the QueryDataGlobal class."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from mikeio1d.res1d import Res1D

from .query_data import QueryData
from ..quantities import TimeSeriesId
from ..quantities import TimeSeriesIdGroup


class QueryDataGlobal(QueryData):
    """A query object that declares what global data to extract from a .res1d file.

    Parameters
    ----------
    quantity: str
        e.g. 'TimeStep'. Call res1d.quantities to get all quantities.
    validate: bool
        Flag specifying to validate the query.

    Examples
    --------
    `QueryDataGlobal('TimeStep')` is a valid query.

    """

    def __init__(self, quantity, validate=True):
        super().__init__(quantity, validate=validate)

    def get_values(self, res1d):
        """Get the time series data for the query."""
        self._check_invalid_quantity(res1d)

        data_item = res1d.global_data[self._quantity]
        values = data_item.CreateTimeSeriesData(0)

        self._check_invalid_values(values)

        return self.from_dotnet_to_python(values)

    def to_timeseries_id(self) -> TimeSeriesId:
        """Convert to TimeSeriesId."""
        tsid = TimeSeriesId(
            quantity=self.quantity,
            group=TimeSeriesIdGroup.GLOBAL,
        )
        return tsid

    def _update_query(self, res1d: Res1D):
        pass

    @staticmethod
    def from_timeseries_id(timeseries_id: TimeSeriesId) -> QueryDataGlobal:
        """Create a QueryDataGlobal from a TimeSeriesId."""
        return QueryDataGlobal(timeseries_id.quantity, validate=False)

    def __repr__(self):
        """Return a string representation of the query."""
        return self._quantity
