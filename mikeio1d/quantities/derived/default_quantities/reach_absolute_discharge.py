from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from typing import List

    import pandas as pd

    from mikeio1d.result_network import ResultLocation

from ..derived_quantity import DerivedQuantity
from ...timeseries_id import TimeSeriesIdGroup


class ReachAbsoluteDischarge(DerivedQuantity):
    _NAME = "ReachAbsoluteDischarge"
    _GROUPS = {TimeSeriesIdGroup.REACH}
    _SOURCE_QUANTITY = "Discharge"

    def derive(self, df_source: pd.DataFrame, locations: List[ResultLocation]):
        df_derived = df_source.abs()
        return df_derived
