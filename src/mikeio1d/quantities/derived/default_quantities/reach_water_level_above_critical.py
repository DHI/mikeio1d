"""ReachWaterLevelAboveCritical class."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from typing import List

    import pandas as pd

    from mikeio1d.result_network import ResultLocation
    from mikeio1d.result_network import ResultGridPoint

import numpy as np

from ..derived_quantity import DerivedQuantity
from ...timeseries_id import TimeSeriesIdGroup


class ReachWaterLevelAboveCritical(DerivedQuantity):
    """Derived quantity for water level above critical level in a reach."""

    _NAME = "ReachWaterLevelAboveCritical"
    _GROUPS = {TimeSeriesIdGroup.REACH}
    _SOURCE_QUANTITY = "WaterLevel"

    def derive(self, df_source: pd.DataFrame, locations: List[ResultLocation]):
        """Derive the water level above critical level in a reach."""
        dtype = df_source.dtypes.iloc[0]
        critical_levels = np.fromiter(self.get_critical_levels(locations), dtype=dtype)
        df_derived = df_source - critical_levels
        return df_derived

    def get_critical_level(self, gridpoint: ResultGridPoint):
        """Get the critical level for a gridpoint."""
        return gridpoint.result_reach.interpolate_reach_critical_level(gridpoint.chainage)

    def get_critical_levels(self, gridpoints: List[ResultGridPoint]):
        """Get the critical levels for a list of gridpoints."""
        yield from (self.get_critical_level(location) for location in gridpoints)
