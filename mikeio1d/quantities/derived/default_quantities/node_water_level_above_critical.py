"""NodeWaterLevelAboveCritical class."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from typing import List

    import pandas as pd

    from mikeio1d.result_network import ResultLocation

from ..derived_quantity import DerivedQuantity
from ...timeseries_id import TimeSeriesIdGroup

import numpy as np


class NodeWaterLevelAboveCritical(DerivedQuantity):
    """Derived quantity for water level above critical level in a node."""

    _NAME = "NodeWaterLevelAboveCritical"
    _GROUPS = {TimeSeriesIdGroup.NODE}
    _SOURCE_QUANTITY = "WaterLevel"

    def derive(self, df_source: pd.DataFrame, locations: List[ResultLocation]) -> pd.DataFrame:
        """Derive the water level above critical level in a node."""
        dtype = df_source.dtypes.iloc[0]
        levels = np.fromiter(self.get_critical_levels(locations), dtype=dtype)
        df_derived = df_source - levels

        return df_derived

    def get_critical_level(self, location: ResultLocation):
        """Get the critical level for a location."""
        return getattr(location, "critical_level", np.nan)

    def get_critical_levels(self, locations: List[ResultLocation]):
        """Get the critical levels for a list of locations."""
        yield from (self.get_critical_level(location) for location in locations)
