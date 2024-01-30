from __future__ import annotations

from typing import TYPE_CHECKING

from typing import Callable

if TYPE_CHECKING:
    from typing import Any
    from typing import List
    from typing import Dict

from dataclasses import fields

import pandas as pd

from mikeio1d.pandas_extension import groupby_level
from mikeio1d.pandas_extension import compact_dataframe
from mikeio1d.various import make_list_if_not_iterable
from mikeio1d.quantities import TimeSeriesId


class ResultFrameAggregator:
    """
    Aggregates a MIKE IO 1D result DataFrame into scalar values associate with entities.

    Parameters
    ----------
    agg : str or callable
        Default aggregation strategy for all levels.
    override_name : str
        Set a custom name for the overall aggregation.
    **kwargs
        Aggregation strategies for specific levels (e.g. time='min', chainage='mean')

    Attributes
    ----------
    entity_levels : list of str
        Entity levels are the geometric entities that the DataFrames are ultimately grouped by.
    agg_levels : list of str
        Agg levels are the levels that are aggregated along.
    agg_strategies : dict of str: callable
        Agg strategies are the strategies used for aggregation.

    Examples
    --------
    # Aggregate along chainage and time, taking the max of each quantity
    >>> agg = ResultFrameAggregator('max')
    >>> agg.aggregate(df)

    # Always take the first chainage value, but take the max of time
    >>> agg = ResultFrameAggregator('max', chainage='first')
    >>> agg.aggregate(df)

    # Same result as above, but with explicit argument names.
    >>> agg = ResultFrameAggregator(time='max', chainage='first')
    """

    def __init__(self, agg: str | Callable = None, override_name: str = None, **kwargs):
        kwargs.setdefault("time", agg)
        if kwargs["time"] is None:
            raise ValueError("Must specify an aggregation strategy for time.")
        if agg is None:
            agg = kwargs["time"]

        self._override_name = override_name
        self._agg_level_name = "agg"

        self._entity_levels = ("group", "name", "tag")
        self._agg_levels = ("duplicate", "chainage", "time")
        self._quantity_levels = ("quantity", "derived")
        self._agg_strategies = self._init_agg_strategies(agg, kwargs)

        self._validate()

    def _init_agg_strategies(self, agg, agg_kwargs: Dict) -> Dict[str, Any]:
        """
        Initialize the aggregation strategies. Default is to use same everywhere.
        """
        strategies = {k: agg for k in self._agg_levels}
        for k, v in agg_kwargs.items():
            if k in strategies:
                strategies[k] = v
        return strategies

    def _validate(self):
        self._validate_levels()
        self._validate_agg_strategies()

    def _validate_levels(self):
        """
        Validate that the entity levels and agg levels are consistent with TimeSeriesId.
        """
        entity_levels = set(self._entity_levels)
        agg_levels = set(self._agg_levels)
        quantity_levels = set(self._quantity_levels)

        if len(entity_levels) != len(self._entity_levels):
            raise ValueError("Entity levels must be unique.")

        if len(agg_levels) != len(self._agg_levels):
            raise ValueError("Agg levels must be unique.")

        if len(quantity_levels) != len(self._quantity_levels):
            raise ValueError("Quantity levels must be unique.")

        if (
            not entity_levels.isdisjoint(agg_levels)
            and not agg_levels.isdisjoint(quantity_levels)
            and not quantity_levels.isdisjoint(entity_levels)
        ):
            raise ValueError("Entity, quantity, and agg levels must be mutually exclusive sets.")

        timeseries_id_fields = set(f.name for f in fields(TimeSeriesId))

        agg_levels.discard("time")  # time is not a field in TimeSeriesId

        if not (entity_levels | agg_levels | quantity_levels) == timeseries_id_fields:
            raise ValueError(
                "Either entity_levels, quantity_levels, or agg_levels is missing a field from TimeSeriesId."
            )

        if self._agg_levels[-1] != "time":
            raise ValueError("Agg levels must end with 'time'.")

        if self._agg_levels[0] != "duplicate":
            raise ValueError("Agg levels should start with 'duplicate'.")

    def _validate_agg_strategies(self):
        """
        Validate that the agg strategies are complete and valid.
        """
        strategies = set(self._agg_strategies.keys())
        if not strategies == set(self._agg_levels):
            raise ValueError("Missing aggregation strategy for one of the agg_levels.")

        for level_name, agg in self._agg_strategies.items():
            self._validate_agg_strategy(level_name, agg)

    def _validate_agg_strategy(self, level_name: str, agg: Any):
        """
        Validate that the agg strategy is a callable or a string.
        """
        if level_name not in self._agg_levels:
            raise ValueError(f"Level name {level_name} is not a valid level for aggregation.")

        valid_agg_types = (str, Callable)
        if not isinstance(agg, valid_agg_types):
            raise ValueError(
                f"Agg strategy for level {level_name} invalid. Must be one of {valid_agg_types}"
            )

    def aggregate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Aggregate along the chainage and time dimensions.
        """
        self._validate_df(df)

        # df = compact_dataframe(df)
        # df = self._remove_group_level(df)

        for agg_level in self._agg_levels[:-1]:
            agg = self.get_agg_strategy(agg_level)
            df = self._aggregate_along_level(df, agg_level, agg)

        agg_time = self.get_agg_strategy("time")
        df = self._aggregate_along_time(df, agg_time)

        df = self._finalize_df_post_aggregate(df)

        return df

    @property
    def entity_levels(self) -> List[str]:
        """
        Entity levels are the geometric entities that the DataFrames are ultimately grouped by.
        """
        return self._entity_levels

    @property
    def agg_levels(self) -> List[str]:
        """
        Agg levels are the levels that are aggregated along.
        """
        return self._agg_levels

    @property
    def quantity_levels(self) -> List[str]:
        """
        Quantity levels are the levels which uniquely identify a quantity.
        """
        return self._quantity_levels

    @property
    def agg_strategies(self) -> Dict[str, Any]:
        """
        Agg strategies are the strategies used for aggregation.
        """
        return self._agg_strategies

    def set_agg_strategy(self, level_name: str, agg: Any):
        """
        Set the aggregation strategy for a level.

        Parameters
        ----------
        level_name : str
            The level name to aggregate along. Must be one of the agg_levels.
        agg : pd.DataFrame.agg func-like
            The aggregation strategy.
        """
        self._validate_agg_strategy(level_name, agg)
        self._agg_strategies[level_name] = agg

    def get_agg_strategy(self, level_name: str) -> Any:
        """
        Get the aggregation strategy for a level.

        Parameters
        ----------
        level_name : str
            The level name to aggregate along. Must be one of the agg_levels.

        Returns
        -------
        agg : pd.DataFrame.agg func-like
            The aggregation strategy.
        """
        agg = self._agg_strategies.get(level_name, None)

        if agg is None:
            raise ValueError(f"No aggregation strategy for level {level_name}.")

        return agg

    def _validate_df(self, obj):
        if not isinstance(obj, pd.DataFrame):
            raise AttributeError("Must be pd.DataFrame.")
        df: pd.DataFrame = obj
        if not isinstance(df.columns, pd.MultiIndex):
            raise AttributeError("Must have a MultiIndex columns.")

    def _has_level_name(self, df: pd.DataFrame, level_name) -> bool:
        return level_name in df.columns.names

    def _remove_group_level(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Remove the group level, if it exists. If there are multiple groups, raise an error.
        """
        if self._has_level_name(df, "group"):
            group_values = df.columns.get_level_values("group")
            number_of_unique_group_values = len(set(group_values))
            if number_of_unique_group_values != 1:
                raise ValueError(
                    f"DataFrame has multiple groups: {set(group_values)}. Cannot aggregate."
                )
            df = df.droplevel("group", axis=1)
        return df

    def _aggregate_along_level(self, df: pd.DataFrame, level: str, agg: Any) -> pd.DataFrame:
        """
        Aggregate along the field dimension.
        """
        if not self._has_level_name(df, level):
            return df

        agg = make_list_if_not_iterable(agg)
        df = groupby_level(df, level_name=level).agg(agg)
        return df

    def _aggregate_along_time(self, df: pd.DataFrame, agg: Any) -> pd.DataFrame:
        """
        Aggregate along the time dimension.
        """
        agg = make_list_if_not_iterable(agg)
        return df.agg(agg)

    def _finalize_quantity_index(self, quantity_index: pd.Index) -> pd.Index:
        """
        Finalize format of quantity_index.
        """
        if len(self._quantity_levels) == 1:
            return quantity_index

        levels_to_keep = ["quantity", self._agg_level_name]
        for level in self._quantity_levels:
            if level not in levels_to_keep:
                quantity_index = quantity_index.droplevel(level)

        quantity_index = quantity_index.map("_".join)

        return quantity_index

    def _finalize_entity_index(self, entity_index: pd.Index) -> pd.Index:
        """
        Finalize format of entity_index.
        """
        if len(self._entity_levels) == 1:
            return entity_index

        levels_to_keep = ["name"]
        for level in self._entity_levels:
            if level in levels_to_keep:
                continue

            is_singular = entity_index.get_level_values(level).nunique() == 1
            if is_singular:
                entity_index = entity_index.droplevel(level)

        return entity_index

    def _finalize_df_post_aggregate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Finalize the DataFrame formatting after aggregation.
        """

        df = df.rename_axis(self._agg_level_name)
        df = df.stack(self._quantity_levels).T

        df.columns = self._finalize_quantity_index(df.columns)
        df.index = self._finalize_entity_index(df.index)

        df = df.sort_index()
        return df
