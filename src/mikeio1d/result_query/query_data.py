"""Module for QueryData base class."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from ..res1d import Res1D

from abc import ABC
from abc import abstractmethod

import numpy as np

from ..custom_exceptions import NoDataForQuery
from ..custom_exceptions import InvalidQuantity
from ..various import NAME_DELIMITER
from ..quantities import TimeSeriesId


class QueryData(ABC):
    """Base query class that declares what data to extract from a .res1d file.

    Parameters
    ----------
    quantity: str
        e.g. 'WaterLevel', 'Discharge', etc. Call res1d.quantities to get all quantities.
    name: str
        Name or ID of location under interest.
    validate: bool
        Flag specifying to validate the query.

    """

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

    @abstractmethod
    def to_timeseries_id(self) -> TimeSeriesId:
        """Convert query to timeseries id."""
        ...

    @staticmethod
    @abstractmethod
    def from_timeseries_id(timeseries_id: TimeSeriesId) -> QueryData:
        """Create query from TimeSeriesId."""
        ...

    @staticmethod
    def from_dotnet_to_python(array):
        """Convert .NET array to numpy."""
        return np.fromiter(array, np.float64)

    @property
    def quantity(self):
        """Return the quantity."""
        return self._quantity

    @property
    def name(self):
        """Return the name."""
        return self._name

    @abstractmethod
    def _update_query(self, res1d: Res1D): ...

    def _check_invalid_quantity(self, res1d: Res1D):
        if self._quantity not in res1d.quantities:
            raise InvalidQuantity(
                f"Undefined quantity {self._quantity}. "
                f"Allowed quantities are: {', '.join(res1d.quantities)}."
            )

    def _check_invalid_values(self, values):
        if values is None:
            raise NoDataForQuery(str(self))

    def __repr__(self):
        """Return the string representation of the query."""
        return NAME_DELIMITER.join([self._quantity, self._name])
