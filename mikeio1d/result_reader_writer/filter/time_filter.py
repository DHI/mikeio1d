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

from .filter import SubFilter
from ...dotnet import to_dotnet_datetime


class TimeFilter(SubFilter):
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

        time = self._time
        start, end = None, None
        if isinstance(time, slice):
            start = time.start
            end = time.stop
        elif isinstance(time, tuple) or isinstance(time, list):
            start, end = time
        else:
            raise ValueError("time parameter must be a slice, tuple or list")

        if start is not None:
            start = pd.to_datetime(start)

        if end is not None:
            end = pd.to_datetime(end)

        period = self.create_period(start, end)
        filter.Periods.Add(period)

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
