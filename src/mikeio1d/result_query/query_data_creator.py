"""Module for creating QueryData objects from TimeSeriesId."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from mikeio1d.quantities import TimeSeriesId
    from .query_data import QueryData

from .query_data_global import QueryDataGlobal
from .query_data_node import QueryDataNode
from .query_data_reach import QueryDataReach
from .query_data_structure import QueryDataStructure
from .query_data_catchment import QueryDataCatchment

from mikeio1d.quantities import TimeSeriesIdGroup


class QueryDataCreator:
    """Factory class for creating QueryData objects from TimeSeriesId."""

    @staticmethod
    def from_timeseries_id(timeseries_id: TimeSeriesId) -> QueryData:
        """Create query from TimeSeriesIdGroup."""
        if timeseries_id.derived:
            raise ValueError("Cannot create QueryData from derived TimeSeriesId.")

        group = timeseries_id.group
        if group == TimeSeriesIdGroup.GLOBAL:
            return QueryDataGlobal.from_timeseries_id(timeseries_id)
        elif group == TimeSeriesIdGroup.NODE:
            return QueryDataNode.from_timeseries_id(timeseries_id)
        elif group == TimeSeriesIdGroup.REACH:
            return QueryDataReach.from_timeseries_id(timeseries_id)
        elif group == TimeSeriesIdGroup.STRUCTURE:
            return QueryDataStructure.from_timeseries_id(timeseries_id)
        elif group == TimeSeriesIdGroup.CATCHMENT:
            return QueryDataCatchment.from_timeseries_id(timeseries_id)
        else:
            raise ValueError(f"Could not create QueryData object for TimeSeriesId group: {group}")
