from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import List

    import pandas as pd

    from mikeio1d.result_network import ResultLocation

from ..derived_quantity import DerivedQuantity
from ...timeseries_id import TimeSeriesIdGroup


class ReachFilling(DerivedQuantity):
    _NAME = "ReachFilling"
    _GROUPS = {TimeSeriesIdGroup.REACH}
    _SOURCE_QUANTITY = "WaterLevel"

    def derive(self, df_source: pd.DataFrame, locations: List[ResultLocation]):
        bottom_levels = tuple(gridpoint.bottom_level for gridpoint in locations)
        heights = tuple(gridpoint.result_reach.height for gridpoint in locations)
        df_derived = (df_source - bottom_levels) / heights
        return df_derived
