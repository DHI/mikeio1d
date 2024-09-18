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
    _NAME = "NodeWaterLevelAboveCritical"
    _GROUPS = {TimeSeriesIdGroup.NODE}
    _SOURCE_QUANTITY = "WaterLevel"

    def derive(self, df_source: pd.DataFrame, locations: List[ResultLocation]) -> pd.DataFrame:

        levels = np.array(
            tuple(self.get_critical_level(location) for location in locations), dtype=np.float32
        )
        df_derived = df_source - levels

        return df_derived

    def get_critical_level(self, location: ResultLocation):
        return getattr(location, "critical_level", np.nan)
