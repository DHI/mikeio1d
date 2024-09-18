from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from typing import List

    import pandas as pd

    from mikeio1d.result_network import ResultLocation

from ..derived_quantity import DerivedQuantity
from ...timeseries_id import TimeSeriesIdGroup


class ReachFlooding(DerivedQuantity):
    _NAME = "ReachFlooding"
    _GROUPS = {TimeSeriesIdGroup.REACH}
    _SOURCE_QUANTITY = "WaterLevel"

    def derive(self, df_source: pd.DataFrame, locations: List[ResultLocation]):
        ground_levels = tuple(
            gridpoint.result_reach.interpolate_reach_ground_level(gridpoint.chainage)
            for gridpoint in locations
        )
        df_derived = df_source - ground_levels
        return df_derived
