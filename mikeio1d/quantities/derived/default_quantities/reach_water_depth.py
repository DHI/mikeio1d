"""ReachWaterDepth class."""

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


class ReachWaterDepth(DerivedQuantity):
    """Reach water depth derived quantity."""

    _NAME = "ReachWaterDepth"
    _GROUPS = {TimeSeriesIdGroup.REACH}
    _SOURCE_QUANTITY = "WaterLevel"

    def derive(self, df_source: pd.DataFrame, locations: List[ResultLocation]):
        """Derive the water depth in a reach."""
        dtype = df_source.dtypes.iloc[0]
        bottom_levels = np.fromiter(self.get_bottom_levels(locations), dtype=dtype)
        df_derived = df_source - bottom_levels
        return df_derived

    def get_bottom_level(self, gridpoint: ResultGridPoint):
        """Get the bottom level for a gridpoint."""
        return gridpoint.bottom_level

    def get_bottom_levels(self, gridpoints: List[ResultGridPoint]):
        """Get the bottom levels for a list of gridpoints."""
        yield from (self.get_bottom_level(location) for location in gridpoints)
