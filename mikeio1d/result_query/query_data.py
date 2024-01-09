from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..result_network.result_quantity import ResultQuantity

import numpy as np

from ..custom_exceptions import NoDataForQuery
from ..custom_exceptions import InvalidQuantity
from ..various import NAME_DELIMITER
from ..quantities import TimeseriesId


class QueryData:
    """
    Base query class that declares what data to extract from a .res1d file.

    Parameters
    ----------
    quantity: str
        e.g. 'WaterLevel', 'Discharge', etc. Call res1d.quantities to get all quantities.
    name: str
        Name or ID of location under interest.
    validate: bool
        Flag specifying to validate the query.
    """

    delete_value = -1e-30

    def __init__(self, quantity, name=None, validate=True):
        self._name = name
        self._quantity = quantity

        if validate:
            self._validate()

    def _validate(self):
        if not isinstance(self.quantity, str):
            raise TypeError("Quantity must be a string.")

        if self.name is not None and not isinstance(self.name, str):
            raise TypeError("Argument 'name' must be either None or a string.")

    def add_to_data_entries(self, res1d, data_entries, timeseries_ids):
        self._check_invalid_quantity(res1d)

        self._update_query(res1d)

        query_label = str(self)
        result_quantity: ResultQuantity = res1d.result_network.result_quantity_map.get(
            query_label, None
        )

        self._check_invalid_values(result_quantity)

        timeseries_id = TimeseriesId.from_result_quantity(result_quantity)
        timeseries_ids.append(timeseries_id)

        data_entry = result_quantity.get_data_entry_net()
        data_entries.Add(data_entry)

    @staticmethod
    def from_dotnet_to_python(array):
        """Convert .NET array to numpy."""
        return np.fromiter(array, np.float64)

    @property
    def quantity(self):
        return self._quantity

    @property
    def name(self):
        return self._name

    def _update_query(self, res1d):
        pass

    def _check_invalid_quantity(self, res1d):
        if self._quantity not in res1d.quantities:
            raise InvalidQuantity(
                f"Undefined quantity {self._quantity}. "
                f"Allowed quantities are: {', '.join(res1d.quantities)}."
            )

    def _check_invalid_values(self, values):
        if values is None:
            raise NoDataForQuery(str(self))

    def __repr__(self):
        return NAME_DELIMITER.join([self._quantity, self._name])
