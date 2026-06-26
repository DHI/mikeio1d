"""ResultFrameAggregator class."""

from __future__ import annotations

from typing import TYPE_CHECKING

from typing import Callable

if TYPE_CHECKING:  # pragma: no cover
    from typing import Any
    from typing import List
    from typing import Dict

from dataclasses import fields

import pandas as pd

from . import groupby_level

from mikeio1d.quantities import TimeSeriesId


class ResultFrameAggregator:
    """Aggregates a MIKE IO 1D result DataFrame with hierarchical columns along specific levels.

    Levels are categorized as entity levels, quantity levels, and aggregation levels.
    Aggregation is only performed along aggregation levels. Quantity levels define the
    resulting DataFrame's columns. Entity levels define the resulting DataFrame's indices.

    Parameters
    ----------
    agg : str or callable, optional
        Default aggregation function to be applied along DataFrame column levels.
        Any str or callable accepted by pd.DataFrame.agg may be used.

        Example:
        - "max"   :  Take the maximum value.
        - "min"   :  Take the minimum value.
        -  np.mean: Take the mean value.

        If not specified, then the 'time' parameter must be provided and is used as default.
    override_name : str, optional
        Set a custom name for the overall aggregation. By default uses the agg function name.
    **kwargs
        Aggregation functions for specific DataFrame column levels (e.g. time='min', chainage='mean')

    Attributes
    ----------
    entity_levels : list of str
        The DataFrame column levels used to uniquely identify an entity.
        (e.g. ['group','name','tag']).
    quantity_levels: list or str
        The DataFrame column levels used to uniquely identify a quantity
        (e.g. ['quantity','derived']).
    agg_levels : list of str
        The DataFrame column levels that will be aggregated along, in order.
        (e.g. ['duplicate','chainage','time']).
    agg_functions : dict of str: callable
        A dictionary with keys matching agg_levels, and values being the aggregation functions.

    Examples
    --------
    # See which levels will be aggregated, and in what order.
    >>> agg = ResultFrameAggregator('max')
    >>> agg.agg_levels
    ['duplicate', 'chainage', 'time']

    # Aggregate along duplicate, chainage, and time, taking the max of each quantity
    >>> agg = ResultFrameAggregator('max')
    >>> agg.aggregate(df)

    # Always take the first chainage value, but take the max of all other levels.
    >>> agg = ResultFrameAggregator('max', chainage='first')
    >>> agg.aggregate(df)

    # Same result as above, but with explicit argument names.
    >>> agg = ResultFrameAggregator(duplicate='max', time='max', chainage='first')
    >>> agg.aggregate(df)

    # Same as above, but recognizing that time='max' becomes the default for unspecifed levels.
    >>> agg = ResultFrameAggregator(chainage='first' time='max')
    >>> agg.aggregate(df)

    """

    def __init__(self, agg: str | Callable = None, override_name: str = None, **kwargs):
        kwargs.setdefault("time", agg)
        if kwargs["time"] is None:
            raise ValueError("Must specify an aggregation function for time.")
        if agg is None:
            agg = kwargs["time"]

        self._override_name = override_name
        self._agg_level_name = "agg"

        self._entity_levels = ("group", "name", "tag")
        self._agg_levels = ("duplicate", "chainage", "time")
        self._quantity_levels = ("quantity", "derived")
        self._agg_functions = self._create_agg_functions_dict(agg, kwargs)

        self._validate()

    def _create_agg_functions_dict(
        self, agg_default: str | Callable, agg_kwargs: Dict
    ) -> Dict[str, Any]:
        """Create the 'agg_functions' attribute dictionary from the supplied aggregation functions."""
        agg_functions = {level: agg_default for level in self._agg_levels}
        for level, func in agg_kwargs.items():
            if level in agg_functions:
                agg_functions[level] = func
        return agg_functions

    def _validate(self):
        self._validate_levels()
        self._validate_agg_functions()

    def _validate_levels(self):
        """Validate that entity, quantity, and agg levels are consistent with TimeSeriesId."""
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

    def _validate_agg_functions(self):
        """Validate that the agg functions are complete and valid."""
        functions = set(self._agg_functions.keys())
        if not functions == set(self._agg_levels):
            raise ValueError("Missing aggregation function for one of the agg_levels.")

        for level_name, agg in self._agg_functions.items():
            self._validate_agg_function(level_name, agg)

    def _validate_agg_function(self, level_name: str, agg: Any):
        """Validate that the agg function is a callable or a string."""
        if level_name not in self._agg_levels:
            raise ValueError(f"Level name '{level_name}' is not a valid level for aggregation.")

        valid_agg_types = (str, Callable)
        if not isinstance(agg, valid_agg_types):
            raise ValueError(
                f"Agg function for level '{level_name}' invalid. Must be one of {valid_agg_types}"
            )

    def aggregate(self, df: pd.DataFrame) -> pd.DataFrame:
        """Aggregate along the duplicate, chainage, and time dimensions."""
        self._validate_df(df)

        for agg_level in self._agg_levels[:-1]:
            agg = self.get_agg_function(agg_level)
            df = self._aggregate_along_level(df, agg_level, agg)

        agg_time = self.get_agg_function("time")
        df = self._aggregate_along_time(df, agg_time)

        df = self._finalize_df_post_aggregate(df)

        return df

    @property
    def entity_levels(self) -> List[str]:
        """The DataFrame column levels used to uniquely identify an entity. (e.g. ['group','name','tag'])."""
        return self._entity_levels

    @property
    def agg_levels(self) -> List[str]:
        """The DataFrame column levels that will be aggregated along, in order. (e.g. ['duplicate','chainage','time'])."""
        return self._agg_levels

    @property
    def quantity_levels(self) -> List[str]:
        """The DataFrame column levels used to uniquely identify a quantity (e.g. ['quantity','derived'])."""
        return self._quantity_levels

    @property
    def agg_functions(self) -> Dict[str, Any]:
        """A dictionary with keys matching agg_levels, and values being the aggregation functions."""
        return self._agg_functions

    def set_agg_function(self, level_name: str, agg: Any):
        """Set the aggregation function for a level.

        Parameters
        ----------
        level_name : str
            The level name to aggregate along. Must be one of the agg_levels.
        agg : pd.DataFrame.agg func-like
            The aggregation function.

        """
        self._validate_agg_function(level_name, agg)
        self._agg_functions[level_name] = agg

    def get_agg_function(self, level_name: str) -> Any:
        """Get the aggregation function for a level.

        Parameters
        ----------
        level_name : str
            The level name to aggregate along. Must be one of the agg_levels.

        Returns
        -------
        agg : pd.DataFrame.agg func-like
            The aggregation function.

        """
        agg = self._agg_functions.get(level_name, None)

        if agg is None:
            raise ValueError(f"No aggregation function for level {level_name}.")

        return agg

    def _validate_df(self, obj):
        if not isinstance(obj, pd.DataFrame):
            raise AttributeError("Must be pd.DataFrame.")
        df: pd.DataFrame = obj
        if not isinstance(df.columns, pd.MultiIndex):
            raise AttributeError("Must have a MultiIndex columns.")

    def _has_level_name(self, df: pd.DataFrame, level_name) -> bool:
        return level_name in df.columns.names

    def _aggregate_along_level(self, df: pd.DataFrame, level: str, agg: Any) -> pd.DataFrame:
        """Aggregate along the specified column level."""
        if not self._has_level_name(df, level):
            return df

        df = groupby_level(df, level_name=level).agg([agg])
        return df

    def _aggregate_along_time(self, df: pd.DataFrame, agg: Any) -> pd.DataFrame:
        """Aggregate along the time dimension (the rows of the DataFrame)."""
        return df.agg([agg])

    def _finalize_quantity_index(self, quantity_index: pd.Index) -> pd.Index:
        """Finalize format of quantity_index."""
        if len(self._quantity_levels) == 1:
            return quantity_index

        levels_to_keep = ["quantity", self._agg_level_name]
        for level in self._quantity_levels:
            if level in levels_to_keep:
                continue
            if level not in quantity_index.names:
                continue
            quantity_index = quantity_index.droplevel(level)

        if self._override_name is not None:
            quantity_index = quantity_index.set_levels(
                quantity_index.levels[quantity_index.names.index(self._agg_level_name)].map(
                    lambda _: self._override_name
                ),
                level=self._agg_level_name,
            )

        quantity_index = quantity_index.map("_".join)

        return quantity_index

    def _finalize_entity_index(self, entity_index: pd.Index) -> pd.Index:
        """Finalize format of entity_index."""
        if len(self._entity_levels) == 1:
            return entity_index

        levels_to_keep = ["name"]
        for level in self._entity_levels:
            if level in levels_to_keep:
                continue
            if level not in entity_index.names:
                continue

            is_singular = False
            data = entity_index.get_level_values(level).to_numpy()
            if data.shape[0] == 1 or (data[0] == data).all():
                is_singular = True

            if is_singular:
                entity_index = entity_index.droplevel(level)

        return entity_index

    def _finalize_df_post_aggregate(self, df: pd.DataFrame) -> pd.DataFrame:
        """Finalize the DataFrame formatting after aggregation."""
        df = df.rename_axis(self._agg_level_name)
        for level in self._quantity_levels:
            if level not in df.columns.names:
                continue
            df = df.stack(level, future_stack=True)  # noqa: PD013 - convert to .melt in future

        df = df.T

        df.columns = self._finalize_quantity_index(df.columns)
        df.index = self._finalize_entity_index(df.index)

        df = df.sort_index()
        return df
