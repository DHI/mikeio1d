from __future__ import annotations

from dataclasses import fields

import pandas as pd

from ..quantities import TimeSeriesId


def compact_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert a DataFrame with a hierarchical column index to a compact DataFrame.

    A compact DataFrame removes levels where every value matches the TimeSeriesId default value.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with hierarchical column index.

    Returns
    -------
    df : pd.DataFrame
        Compact DataFrame.
    """
    index = df.columns

    is_hierarchical_index = isinstance(index, pd.MultiIndex)
    if not is_hierarchical_index:
        raise ValueError("DataFrame must have a hierarchical column index to compact.")

    for field in fields(TimeSeriesId):
        level_values = index.get_level_values(field.name)
        is_only_one_unique_value = len(level_values.unique()) == 1
        if not is_only_one_unique_value:
            continue
        level_value = level_values[0]
        is_all_default_values = (level_value == field.default) or (
            level_value != level_value and field.default != field.default
        )
        if is_all_default_values:
            index = index.droplevel(field.name)

    df.columns = index
    return df
