"""ReachAbsoluteDischarge class."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import ClassVar

if TYPE_CHECKING:  # pragma: no cover
    import pandas as pd

    from mikeio1d.result_network import ResultLocation

from ...timeseries_id import TimeSeriesIdGroup
from ..derived_quantity import DerivedQuantity


class ReachAbsoluteDischarge(DerivedQuantity):
    """Derived quantity for absolute discharge in a reach."""

    _NAME = "ReachAbsoluteDischarge"
    _GROUPS: ClassVar[set[TimeSeriesIdGroup]] = {TimeSeriesIdGroup.REACH}
    _SOURCE_QUANTITY = "Discharge"

    def derive(self, df_source: pd.DataFrame, locations: list[ResultLocation]):
        """Derive the absolute discharge in a reach."""
        df_derived = df_source.abs()
        return df_derived
