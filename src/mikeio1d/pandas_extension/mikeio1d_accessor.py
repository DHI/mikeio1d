"""Provides a custom accessor for Pandas DataFrames."""

import pandas as pd

from .transposed_groupby import TransposedGroupBy
from .result_reaches_helpers import agg_chainage
from .result_reaches_helpers import groupby_chainage
from .various import compact_dataframe
from .various import groupby_level


@pd.api.extensions.register_dataframe_accessor("m1d")
class Mikeio1dAccessor:
    """Uses Pandas Extension API to register a custom accessor for DataFrames.

    More information can be found here:

    https://pandas.pydata.org/docs/development/extending.html#registering-custom-accessors

    The accessor provides convenience methods for working with DataFrames with a MultiIndex.
    The intent is as a facade for various helper functions that live elsewhere in the package.
    """

    def __init__(self, pandas_obj):
        self._validate(pandas_obj)
        self._obj = pandas_obj

    @staticmethod
    def _validate(obj):
        if not isinstance(obj, pd.DataFrame):
            raise AttributeError("Mikeio1dAccessor only supports DataFrames.")
        df: pd.DataFrame = obj
        if not isinstance(df.columns, pd.MultiIndex):
            raise AttributeError("Must have a MultiIndex columns.")

    def _validate_has_chainage(self):
        self._validate(self._obj)
        if "chainage" not in self._obj.columns.names:
            raise ValueError("DataFrame must have chainage column.")

    def agg_chainage(self, agg=None) -> pd.DataFrame:
        """Wrap ResultReaches.agg_chainage."""
        self._validate_has_chainage()
        kwargs = {}
        if agg is not None:
            kwargs["agg"] = agg

        return agg_chainage(self._obj, **kwargs)

    def groupby_chainage(self, *args, **kwargs) -> TransposedGroupBy:
        """Wrap pd.DataFrame.groupby. The groupby is performed on the columns of the DataFrame, which are in the form of a MultiIndex."""
        self._validate_has_chainage()
        df: pd.DataFrame = self._obj
        return groupby_chainage(df, *args, **kwargs)

    def groupby_level(self, level_name: str) -> pd.DataFrame:
        """Wrap groupby_level. The groupby is performed on the columns of the DataFrame, which are in the form of a MultiIndex."""
        self._validate(self._obj)
        df: pd.DataFrame = self._obj
        return groupby_level(df, level_name)

    def groupby(self, *args, **kwargs) -> TransposedGroupBy:
        """Wrap pd.DataFrame.groupby. The groupby is performed on the columns of the DataFrame, which are in the form of a MultiIndex."""
        df: pd.DataFrame = self._obj
        groupby = TransposedGroupBy(transposed_groupby=df.T.groupby(*args, **kwargs))
        return groupby

    def query(self, *args, **kwargs) -> pd.DataFrame:
        """Wrap pd.DataFrame.query. The query is performed on the columns of the DataFrame, which are in the form of a MultiIndex."""
        df = self._obj
        return df.T.query(*args, **kwargs).T

    def compact(self, *args, **kwargs) -> pd.DataFrame:
        """Wrap compact_dataframe."""
        df = self._obj
        return compact_dataframe(df, *args, **kwargs)
