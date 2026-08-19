"""Module for ResultQuantityDerivedCollection class."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    import pandas as pd

    from ..res1d import Res1D
    from ..result_network import ResultLocations
    from ..quantities import DerivedQuantity

from .result_quantity_derived import ResultQuantityDerived


class ResultQuantityDerivedCollection(ResultQuantityDerived):
    """Class for a collection of derived quantities."""

    def __init__(
        self, derived_quantity: DerivedQuantity, result_locations: ResultLocations, res1d: Res1D
    ):
        self.derived_quantity = derived_quantity
        self.result_locations = result_locations
        self.res1d: Res1D = res1d

    def _create_source_dataframe(self) -> pd.DataFrame:
        """Create a data frame with the source quantities for the derived quantity."""
        return self.derived_quantity.create_source_dataframe_for_locations(self.result_locations)
