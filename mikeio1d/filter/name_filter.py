"""Module for the NameFilter class."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from DHI.Mike1D.ResultDataAccess import ResultData
    from DHI.Mike1D.ResultDataAccess import Filter


from . import ResultSubFilter

from DHI.Mike1D.ResultDataAccess import DataItemFilterName


class NameFilter(ResultSubFilter):
    """Wrapper class for applying time filters to a Filter object."""

    def __init__(
        self,
        reaches: None | list[str],
        nodes: None | list[str],
        catchments: None | list[str],
    ):
        self._reaches = reaches if reaches else []
        self._nodes = nodes if nodes else []
        self._catchments = catchments if catchments else []

    def use_filter(self) -> bool:
        """Check if the filter should be used."""
        return any((self._reaches, self._nodes, self._catchments))

    def apply(self, filter: Filter, result_data: ResultData | None):
        """Apply the filter to the provided Filter object."""
        if not self.use_filter():
            return

        data_item_filter = self.create_data_item_filter(result_data)
        filter.AddDataItemFilter(data_item_filter)

    def create_data_item_filter(self, result_data: ResultData) -> DataItemFilterName:
        """Create DataItemFilterName object."""
        data_item_filter = DataItemFilterName(result_data)

        for reach in self._reaches:
            data_item_filter.Reaches.Add(reach)
        for node in self._nodes:
            data_item_filter.Nodes.Add(node)
        for catchment in self._catchments:
            data_item_filter.Catchments.Add(catchment)

        return data_item_filter
