"""Module for the TimeFilter class."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from typing import Union

from datetime import datetime

import pandas as pd

from System import DateTime
from DHI.Mike1D.ResultDataAccess import Period

from ..dotnet import to_dotnet_datetime


class TimeFilter:
    """Wrapper class for applying time filters to a Filter object."""

    def __init__(self, filter):
        self._filter = filter

    def setup_from_user_params(self, *, time: Union[None, slice, tuple, list]):
        """Set up the filter using a user supplied parameters."""
        if time is None:
            return

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

        self.add_period(start, end)

    def add_period(self, start: Union[None, datetime], end: Union[None, datetime]):
        """Add a period to the filter."""
        if start is None and end is None:
            raise ValueError("Either start or end must be provided")

        start = to_dotnet_datetime(start) if start else DateTime.MinValue
        end = to_dotnet_datetime(end) if end else DateTime.MaxValue

        start, end = self._adjust_start_and_end(start, end)

        period = Period(start, end)

        self._filter.Periods.Add(period)

    def _adjust_start_and_end(self, start, end):
        """Adjust start and end times to conservatively ensure they are inclusive."""
        if start != DateTime.MinValue:
            start = start.AddSeconds(-1)
        if end != DateTime.MaxValue:
            end = end.AddSeconds(1)
        return start, end
