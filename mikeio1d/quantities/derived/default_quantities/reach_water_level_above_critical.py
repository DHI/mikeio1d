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
    _NAME = "ReachWaterLevelAboveCritical"
    _GROUPS = {TimeSeriesIdGroup.REACH}
    _SOURCE_QUANTITY = "WaterLevel"

    def derive(self, df_source: pd.DataFrame, locations: List[ResultLocation]):
        dtype = df_source.dtypes.iloc[0]
        critical_levels = np.fromiter(self.get_critical_levels(locations), dtype=dtype)
        df_derived = df_source - critical_levels
        return df_derived

    def get_critical_level(self, gridpoint: ResultGridPoint):
        return gridpoint.result_reach.interpolate_reach_critical_level(
            gridpoint.chainage
        )

    def get_critical_levels(self, gridpoints: List[ResultGridPoint]):
        yield from (self.get_critical_level(location) for location in gridpoints)
