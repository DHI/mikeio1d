"""Module for the TimeFilter class."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from DHI.Mike1D.ResultDataAccess import ResultData
    from DHI.Mike1D.ResultDataAccess import Filter


class StepEveryFilter:
    """Wrapper class for applying step every filter to a Filter object."""

    def __init__(self, step_every: int | None):
        self._step_every = step_every

    def use_filter(self) -> bool:
        """Check if the filter should be used."""
        return self._step_every is not None

    def apply(self, filter: Filter, result_data: ResultData | None = None):
        """Apply the filter to the provided Filter object."""
        if self.use_filter():
            filter.LoadStep = self._step_every
