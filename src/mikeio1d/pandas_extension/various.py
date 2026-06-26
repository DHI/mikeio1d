"""Various functions for working with pandas DataFrames."""

from __future__ import annotations

from dataclasses import fields

import pandas as pd

from ..quantities import TimeSeriesId

from .transposed_groupby import TransposedGroupBy


def compact_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Convert a DataFrame with a hierarchical column index to a compact DataFrame.

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
        if field.name not in index.names:
            continue
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


def groupby_level(df: pd.DataFrame, level_name: str) -> pd.DataFrame:
    """Group DataFrame for aggregations along the specific level name.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with hierarchical column index.
    level_name : str
        Name of level in the hierarchical column index.

    Returns
    -------
    df : pd.DataFrame
        Grouped DataFrame.

    Examples
    --------
    >>> df.m1d.groupby_level("duplicate").first()
    Out[1]: The DataFrame with the first value for each duplicate.

    """
    if level_name not in df.columns.names:
        raise ValueError(f"Level name {level_name} not found in columns.")

    fixed_level_names = [n for n in df.columns.names if n != level_name]
    groupby = df.T.groupby(fixed_level_names, sort=False)
    return TransposedGroupBy(groupby)
