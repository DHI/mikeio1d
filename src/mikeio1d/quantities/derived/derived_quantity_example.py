"""ExampleDerivedQuantity class.

This module contains the ExampleDerivedQuantity class, which is an example of how to create a derived quantity.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from typing import List
    import pandas as pd

    from mikeio1d.result_network import ResultLocation

from mikeio1d.quantities import DerivedQuantity
from mikeio1d.quantities import TimeSeriesIdGroup


class ExampleDerivedQuantity(DerivedQuantity):
    """Example derived quantity."""

    # Replace with the name of the derived quantity
    _NAME = "WaterLevelPlusOne"

    # Replace with the groups that the derived quantity can be applied to
    _GROUPS = {TimeSeriesIdGroup.NODE, TimeSeriesIdGroup.REACH}

    # Replace with the source quantity that the derived quantity is derived from
    _SOURCE_QUANTITY = "WaterLevel"

    def derive(self, df_source: pd.DataFrame, locations: List[ResultLocation]) -> pd.DataFrame:
        """Transform the source quantities into the derived quantity.

        Parameters
        ----------
        df_source : pd.DataFrame
            A DataFrame containing all the required sournce quantities.
        locations : List[ResultLocation]
            A list of ResultLocation objects associated with each column of df_source.

        Returns
        -------
        pd.DataFrame
            A DataFrame containing the derived quantity. Must be the same shape as df_source.
            Additionally, the columns of the DataFrame must be in the same order as df_source.

        """
        # Replace with your derivation logic
        df_derived = df_source + 1

        # Return the derived quantity
        return df_derived
