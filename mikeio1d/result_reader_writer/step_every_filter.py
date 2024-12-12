"""Module for the TimeFilter class."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from DHI.Mike1D.ResultDataAccess import Filter

from ..dotnet import to_dotnet_datetime


class StepEverFilter:
    """Wrapper class for applying step every filter to a Filter object."""

    def __init__(self, filter: Filter):
        self._filter = filter

    def setup_from_user_params(self, step_every: int | None):
        """Set up the filter using a user supplied parameters."""
        if step_every is None:
            return
        self._filter.LoadStep = step_every
