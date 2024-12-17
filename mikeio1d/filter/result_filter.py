"""Filter Class."""

from __future__ import annotations

from typing import Protocol
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from DHI.Mike1D.ResultDataAccess import ResultData
    from DHI.Mike1D.ResultDataAccess import IDataItem

from DHI.Mike1D.ResultDataAccess import Filter


class ResultFilter:
    """Wrapper class for applying subfilters to a Filter object."""

    def __init__(
        self,
        sub_filters: list[ResultSubFilter],
    ):
        self._filter = Filter()
        self.sub_filters = sub_filters

    def use_filter(self) -> bool:
        """Whether the filter should be applied."""
        return any([f.use_filter() for f in self.sub_filters])

    def apply(self, result_data: ResultData):
        """Apply filter."""
        if not self.use_filter():
            return
        for sub_filter in self.sub_filters:
            sub_filter.apply(self._filter, result_data)
        result_data.Parameters.Filter = self._filter

    def is_data_item_included(self, data_item: IDataItem) -> bool:
        """Check if a data item is included in the filter."""
        return self._filter.Include(data_item)

    @property
    def res1d_filter(self) -> Filter:
        """.NET DHI.Mike1D.ResultDataAccess.Filter object."""
        return self._filter


class ResultSubFilter(Protocol):
    """Class for configuring Filter objects."""

    def apply(self, filter: Filter, result_data: ResultData | None) -> None:
        """Apply the filter to the provided Filter object."""
        pass

    def use_filter(self) -> bool:
        """Check if the filter should be used."""
        pass
