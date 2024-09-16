from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import List

    import pandas as pd

    from mikeio1d.result_network import ResultLocation

from ..derived_quantity import DerivedQuantity
from ...timeseries_id import TimeSeriesIdGroup


class ReachWaterLevelAboveCritical(DerivedQuantity):
    _NAME = "ReachWaterLevelAboveCritical"
    _GROUPS = {TimeSeriesIdGroup.REACH}
    _SOURCE_QUANTITY = "WaterLevel"

    def derive(self, df_source: pd.DataFrame, locations: List[ResultLocation]):
        critical_levels = tuple(
            gridpoint.result_reach.interpolate_reach_critical_level(gridpoint.chainage)
            for gridpoint in locations
        )
        df_derived = df_source - critical_levels
        return df_derived
