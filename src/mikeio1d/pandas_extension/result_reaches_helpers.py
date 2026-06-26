"""Helper functions for working with results along the chainage axis."""

import pandas as pd

from .transposed_groupby import TransposedGroupBy


def groupby_chainage(df: pd.DataFrame, **kwargs) -> TransposedGroupBy:
    """Group results for aggregation along the chainage axis.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with results. Must have hierarchical column index (e.g. column_mode = 'all').

    Returns
    -------
    groupby : TransposedGroupBy
        GroupBy object, which can be used for aggregation.

    """
    fixed_level_names = [n for n in df.columns.names if n != "chainage"]
    groupby = TransposedGroupBy(transposed_groupby=df.T.groupby(fixed_level_names, **kwargs))
    return groupby


def agg_chainage(df: pd.DataFrame, agg=["first"], gb_kwargs: dict = {}, **kwargs) -> pd.DataFrame:
    """Aggregate results along the chainage axis.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with results. Must have hierarchical column index (e.g. column_mode = 'all').
    agg : function, str, list or dict
        Aggregation function(s) to apply. Same as pandas.DataFrame.agg.

    Returns
    -------
    df : pd.DataFrame
        DataFrame with aggregated results.

    """
    groupby = groupby_chainage(df, **gb_kwargs)
    return groupby.agg(agg, **kwargs)
