"""TransposedGroupBy class."""

import pandas as pd


class TransposedGroupBy:
    """Same as pandas.DataFrameGroupBy, but returns the transpose of the result.

    Useful where a groupby is performed on a transposed DataFrame, and after
    aggregation the result should be transposed back.

    Parameters
    ----------
    transposed_groupby : pandas.DataFrameGroupBy
        A pandas.DataFrameGroupBy object, which is created from a transposed DataFrame.

    Examples
    --------
    >>> df = res.reaches.read(column_mode='all')
    >>> groupby = TransposedGroupBy(df.T.groupby(['quantity]))
    >>> groupby.agg(['mean', 'max'])
    ... # performs agg function, then returns the transpose of the result.

    """

    def __init__(self, transposed_groupby):
        self.transposed_groupby = transposed_groupby

    def __getattr__(self, name):
        """Return the transposed result of the method."""

        def method(*args, **kwargs):
            result = getattr(self.transposed_groupby, name)(*args, **kwargs)
            if isinstance(result, pd.DataFrame):
                return result.T
            return result

        return method
