"""Module for the NameFilter class."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from DHI.Mike1D.ResultDataAccess import ResultData
    from DHI.Mike1D.ResultDataAccess import Filter


from . import ResultSubFilter

from DHI.Mike1D.ResultDataAccess import DataItemFilterQuantity
from DHI.Mike1D.Generic import Quantity
from DHI.Mike1D.Generic import PredefinedQuantity
from DHI.Mike1D.Generic import PredefinedQuantityTable


class QuantityFilter(ResultSubFilter):
    """Wrapper class for applying quantity filters to a Filter object."""

    def __init__(
        self,
        quantities: None | list[str],
    ):
        self._quantities = quantities if quantities else []
        self._quantities_in_res1d = None
        self._predefined_quantity_table = PredefinedQuantityTable()

    def use_filter(self) -> bool:
        """Check if the filter should be used."""
        return bool(self._quantities)

    def apply(self, filter: Filter, result_data: ResultData | None):
        """Apply the filter to the provided Filter object."""
        if not self.use_filter():
            return

        if result_data is not None:
            self._quantities_in_res1d = {
                quantity.Id: quantity for quantity in result_data.Quantities
            }

        data_item_filter = self.create_data_item_filter()
        filter.AddDataItemFilter(data_item_filter)

    def create_data_item_filter(self) -> DataItemFilterQuantity:
        """Create DataItemFilterName object."""
        data_item_filter = DataItemFilterQuantity()

        for quantity in self._quantities:
            m1d_quantity = self.convert_quantity(quantity)
            data_item_filter.Quantities.Add(m1d_quantity)

        return data_item_filter

    def convert_quantity(self, quantity: str) -> Quantity:
        """Convert string quantity id to corresponding object."""
        if self._quantities_in_res1d is not None:
            m1d_quantity = self._quantities_in_res1d.get(quantity, None)
        else:
            m1d_quantity = self._get_predefined_quantity()

        if m1d_quantity is None:
            raise ValueError(f"Invalid quantity filter: {quantity}")

        return m1d_quantity

    def _get_predefined_quantity(self, quantity: str) -> Quantity:
        predefined_quantity = getattr(PredefinedQuantity, quantity, None)
        if not predefined_quantity:
            return None
        return self._predefined_quantity_table[predefined_quantity]
