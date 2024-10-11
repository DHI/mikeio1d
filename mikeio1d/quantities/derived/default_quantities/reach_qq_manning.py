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


class ReachQQManning(DerivedQuantity):
    _NAME = "ReachQQManning"
    _GROUPS = {TimeSeriesIdGroup.REACH}
    _SOURCE_QUANTITY = "Discharge"

    def derive(self, df_source: pd.DataFrame, locations: List[ResultLocation]):
        dtype = df_source.dtypes.iloc[0]
        full_flow_discharges = np.fromiter(
            self.get_full_flow_discharges(locations), dtype=dtype
        )
        df_derived = df_source / full_flow_discharges
        return df_derived

    def get_full_flow_discharge(self, gridpoint: ResultGridPoint):
        return gridpoint.result_reach.full_flow_discharge

    def get_full_flow_discharges(self, gridpoints: List[ResultGridPoint]):
        yield from (self.get_full_flow_discharge(location) for location in gridpoints)
