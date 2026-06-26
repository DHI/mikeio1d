"""ReachFilling class."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from typing import List

    import pandas as pd

    from mikeio1d.result_network import ResultLocation
    from mikeio1d.result_network import ResultGridPoint
    from mikeio1d.result_network import ResultReach

import numpy as np

from ..derived_quantity import DerivedQuantity
from ...timeseries_id import TimeSeriesIdGroup


class ReachFilling(DerivedQuantity):
    """Derived quantity for filling of a reach."""

    _NAME = "ReachFilling"
    _GROUPS = {TimeSeriesIdGroup.REACH}
    _SOURCE_QUANTITY = "WaterLevel"

    def derive(self, df_source: pd.DataFrame, locations: List[ResultLocation]):
        """Derive the filling of a reach."""
        dtype = df_source.dtypes.iloc[0]
        bottom_levels = np.fromiter(self.get_bottom_levels(locations), dtype=dtype)
        heights = np.fromiter(self.get_heights(locations), dtype=dtype)
        df_derived = (df_source - bottom_levels) / heights
        return df_derived

    def get_bottom_level(self, gridpoint: ResultGridPoint):
        """Get the bottom level for a gridpoint."""
        return getattr(gridpoint, "bottom_level", np.nan)

    def get_bottom_levels(self, gridpoints: List[ResultGridPoint]):
        """Get the bottom levels for a list of gridpoints."""
        yield from (self.get_bottom_level(location) for location in gridpoints)

    def get_height(self, gridpoint: ResultGridPoint):
        """Get the height for a gridpoint."""
        return getattr(gridpoint.result_reach, "height", np.nan)

    def get_heights(self, gridpoints: List[ResultGridPoint]):
        """Get the heights for a list of gridpoints."""
        yield from (self.get_height(location) for location in gridpoints)
