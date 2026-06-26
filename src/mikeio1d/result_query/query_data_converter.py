"""Module for QueryDataConverter Class."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from typing import List

    from ..res1d import Res1D
    from .query_data import QueryData

from ..quantities import TimeSeriesId


class QueryDataConverter:
    """Converter class for converting QueryData objects to TimeSeriesId objects.

    Parameters
    ----------
    query : QueryData
        Query object to convert.

    """

    def __init__(self, query: QueryData):
        self._query = query

    def to_timeseries_id(self, res1d: Res1D) -> TimeSeriesId:
        """Convert query to timeseries id."""
        self._validate_query_with_res1d(res1d)

        time_series_id = self._query.to_timeseries_id()

        if not time_series_id.is_valid(res1d):
            self._query._check_invalid_values(None)

        return time_series_id

    def _validate_query_with_res1d(self, res1d: Res1D):
        """Validate query with res1d object."""
        query = self._query

        query._update_query(res1d)
        query._check_invalid_quantity(res1d)

    @staticmethod
    def convert_queries_to_time_series_ids(
        res1d: Res1D, queries: list[QueryData]
    ) -> List[TimeSeriesId]:
        """Convert queries to TimeSeriesId objects.

        Parameters
        ----------
        res1d : Res1D
            Res1D object (required for query validation)
        queries : list[QueryData]
            List of query objects to convert.

        Returns
        -------
        List[TimeSeriesId]
            List of timeseries ids.

        """
        return [QueryDataConverter(query).to_timeseries_id(res1d) for query in queries]

    @staticmethod
    def convert_time_series_id_to_query(time_series_id: TimeSeriesId) -> QueryData:
        """Convert TimeSeriesId object to QueryData object.

        Parameters
        ----------
        time_series_id : TimeSeriesId
            TimeSeriesId object to convert.

        Returns
        -------
        QueryData
            QueryData object.

        """
        return QueryData.from_timeseries_id(time_series_id)
