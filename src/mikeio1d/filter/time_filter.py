"""Module for the TimeFilter class."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from DHI.Mike1D.ResultDataAccess import ResultData
    from DHI.Mike1D.ResultDataAccess import Filter

from datetime import datetime

import pandas as pd

from System import DateTime
from DHI.Mike1D.ResultDataAccess import Period

from . import ResultSubFilter
from ..dotnet import to_dotnet_datetime


class TimeFilter(ResultSubFilter):
    """Wrapper class for applying time filters to a Filter object."""

    def __init__(self, time: None | slice | tuple | list):
        self._time = time

    def use_filter(self) -> bool:
        """Check if the filter should be used."""
        return self._time is not None

    def apply(self, filter: Filter, result_data: ResultData | None = None):
        """Apply the filter to the provided Filter object."""
        if not self.use_filter():
            return

        time_intervals = self._determine_time_intervals(self._time)

        for time_interval in time_intervals:
            start, end = time_interval
            period = self.create_period(start, end)
            filter.Periods.Add(period)

    def _determine_time_intervals(
        self, time_intervals: None | slice | tuple | list
    ) -> list[tuple[pd.Timestamp, pd.Timestamp]]:
        # In case of slice convert time_intervals to a list containing that slice.
        # Needed to be able to evaluate contains_time_intervals properly.
        time_intervals = [time_intervals] if isinstance(time_intervals, slice) else time_intervals

        contains_time_intervals = (
            all(isinstance(t, slice) for t in time_intervals)
            or all(isinstance(t, tuple) for t in time_intervals)
            or all(isinstance(t, list) for t in time_intervals)
        )

        if contains_time_intervals:
            return [self._determine_start_and_end_time(t) for t in time_intervals]
        else:
            return [self._determine_start_and_end_time(time_intervals)]

    def _determine_start_and_end_time(
        self, time_interval: None | slice | tuple[any, any] | list[any, any]
    ) -> tuple[pd.Timestamp, pd.Timestamp]:
        start, end = None, None

        if isinstance(time_interval, slice):
            start = time_interval.start
            end = time_interval.stop
        elif isinstance(time_interval, tuple) or isinstance(time_interval, list):
            start, end = time_interval
        else:
            raise ValueError("time parameter must be a slice, tuple or list")

        start = self._convert_to_datetime(start)
        end = self._convert_to_datetime(end)

        return (start, end)

    def _convert_to_datetime(self, time: str | datetime) -> pd.Timestamp:
        return pd.to_datetime(time) if time is not None else None

    def create_period(self, start: None | datetime, end: None | datetime) -> Period:
        """Create a DHI.Mike1D.ResultDataAccess.Period object."""
        start = to_dotnet_datetime(start) if start else DateTime.MinValue
        end = to_dotnet_datetime(end) if end else DateTime.MaxValue

        start, end = self._adjust_start_and_end(start, end)

        return Period(start, end)

    def _adjust_start_and_end(self, start, end):
        """Adjust start and end times to conservatively ensure they are inclusive."""
        if start != DateTime.MinValue:
            start = start.AddSeconds(-1)
        if end != DateTime.MaxValue:
            end = end.AddSeconds(1)
        return start, end
