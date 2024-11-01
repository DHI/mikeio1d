"""Module for the QueryDataCatchment class."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from ..res1d import Res1D

from .query_data import QueryData
from ..quantities import TimeSeriesId
from ..quantities import TimeSeriesIdGroup


class QueryDataCatchment(QueryData):
    """A query object that declares what catchment data to extract from a .res1d file.

    Parameters
    ----------
    quantity: str
        e.g. 'TotalRunoff'. Call res1d.quantities to get all quantities.
    name: str, optional
        Catchment name
    validate: bool
        Flag specifying to validate the query.

    Examples
    --------
    `QueryDataCatchment('TotalRunoff', 'catchment1')` is a valid query.

    """

    def __init__(self, quantity, name=None, validate=True):
        super().__init__(quantity, name, validate)

    def get_values(self, res1d: Res1D):
        """Get the time series data for the query."""
        self._check_invalid_quantity(res1d)

        values = res1d.query.GetCatchmentValues(self._name, self._quantity)

        self._check_invalid_values(values)

        return self.from_dotnet_to_python(values)

    def to_timeseries_id(self) -> TimeSeriesId:
        """Convert to TimeSeriesId."""
        tsid = TimeSeriesId(
            quantity=self.quantity,
            group=TimeSeriesIdGroup.CATCHMENT,
            name=self.name,
        )
        return tsid

    def _update_query(self, res1d: Res1D):
        pass

    @staticmethod
    def from_timeseries_id(timeseries_id: TimeSeriesId) -> QueryDataCatchment:
        """Create a QueryDataCatchment from a TimeSeriesId."""
        return QueryDataCatchment(timeseries_id.quantity, timeseries_id.name, validate=False)
