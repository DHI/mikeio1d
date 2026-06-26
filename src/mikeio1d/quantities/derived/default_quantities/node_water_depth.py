"""NodeWaterDepth derived quantity."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from typing import List

    import pandas as pd

    from mikeio1d.result_network import ResultLocation

from ..derived_quantity import DerivedQuantity
from ...timeseries_id import TimeSeriesIdGroup

import numpy as np


class NodeWaterDepth(DerivedQuantity):
    """Derived quantity for water depth in a node."""

    _NAME = "NodeWaterDepth"
    _GROUPS = {TimeSeriesIdGroup.NODE}
    _SOURCE_QUANTITY = "WaterLevel"

    def derive(self, df_source: pd.DataFrame, locations: List[ResultLocation]) -> pd.DataFrame:
        """Derive the water depth in a node."""
        dtype = df_source.dtypes.iloc[0]
        bottom_levels = np.fromiter(self.get_bottom_levels(locations), dtype=dtype)
        df_derived = df_source - bottom_levels

        return df_derived

    def get_bottom_level(self, location: ResultLocation):
        """Get the bottom level for a location."""
        return getattr(location, "bottom_level", np.nan)

    def get_bottom_levels(self, locations: List[ResultLocation]):
        """Get the bottom levels for a list of locations."""
        yield from (self.get_bottom_level(location) for location in locations)
