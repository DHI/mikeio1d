"""Module for the DerivedQuantity class."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from typing import Set
    from typing import List

    from mikeio1d.res1d import Res1D
    from mikeio1d.result_network import ResultLocation
    from mikeio1d.result_network import ResultLocations

from abc import ABC
from abc import abstractmethod

from dataclasses import replace

import pandas as pd

from ..timeseries_id import TimeSeriesId
from ..timeseries_id import TimeSeriesIdGroup


class DerivedQuantity(ABC):
    """Abstract base class for derived quantities."""

    _NAME = None
    _GROUPS = None
    _SOURCE_QUANTITY = None

    def __init__(self, res1d: Res1D):
        self._res1d = res1d
        self._validate()

    def __repr__(self) -> str:
        """Representation of the derived quantity."""
        return f"<{self.__class__.__name__}>"

    def _validate(self) -> bool:
        """Validate the derived quantity.

        Returns
        -------
        bool
            True if the derived quantity is valid, False otherwise.

        """
        if not isinstance(self._NAME, str):
            raise ValueError("DerivedQuantity must have str value for '_NAME'.")
        if not isinstance(self._GROUPS, set):
            raise ValueError("DerivedQuantity must have set value for '_GROUPS'.")
        if not isinstance(self._SOURCE_QUANTITY, str):
            raise ValueError("DerivedQuantity must have str value for '_SOURCE_QUANTITY'.")

    @property
    def res1d(self) -> Res1D:
        """Res1D object."""
        return self._res1d

    @property
    def name(self) -> str:
        """Name of the derived quantity."""
        return self._NAME

    @property
    def groups(self) -> Set[TimeSeriesIdGroup]:
        """List of groups that the derived quantity applies to."""
        return self._GROUPS

    @property
    def source_quantity(self) -> str:
        """Name of the source quantity that the derived quantity is based on."""
        return self._SOURCE_QUANTITY

    @abstractmethod
    def derive(self, df_source: pd.DataFrame, locations: List[ResultLocation]) -> pd.DataFrame:
        """Calculate the derived quantity based on the source quantity.

        Parameters
        ----------
        df : pd.DataFrame
            DataFrame with source quantities for all relevant groups.
        locations : List[ResultLocation]
            List of ResultLocation objects (e.g. ResultNode) associated with each column in df_source.

        Returns
        -------
        pd.DataFrame
            DataFrame with the derived quantity for all relevant groups.

        """
        ...

    def generate(self, df_source: pd.DataFrame = None) -> pd.DataFrame:
        """Generate the derived quantity based on the source quantity.

        Returns
        -------
        pd.DataFrame
            DataFrame with the derived quantity for all relevant groups.

        """
        if df_source is None:
            df_source = self._create_source_dataframe()

        locations = self.get_result_locations_from_source_dataframe(df_source)

        df_derived = self.derive(df_source, locations)

        df_derived.columns = self._create_derived_columns(df_derived.columns)
        df_derived = df_derived.m1d.compact()
        return df_derived

    def create_source_dataframe_for_location(self, result_location: ResultLocation) -> pd.DataFrame:
        """Generate a DataFrame with the source quantities required to calculate the derived quantity.

        Parameters
        ----------
        result_location : ResultLocation
            ResultLocation to generate source quantities for.

        Returns
        -------
        pd.DataFrame
            DataFrame with the source quantities for the specified ResultLocation.

        """
        tsids = self._get_source_timeseries_ids_for_location(result_location)
        df_source = self.res1d.reader.read(tsids, column_mode="compact")
        return df_source

    def create_source_dataframe_for_locations(
        self, result_locations: ResultLocations
    ) -> pd.DataFrame:
        """Generate a DataFrame with the source quantities required to calculate the derived quantity.

        Parameters
        ----------
        result_locations : ResultLocations
            ResultLocations to generate source quantities for.

        Returns
        -------
        pd.DataFrame
            DataFrame with the source quantities for the specified ResultLocations.

        """
        tsids = self._get_source_timeseries_ids_for_locations(result_locations)
        df_source = self.res1d.reader.read(tsids, column_mode="compact")
        return df_source

    def get_result_locations_from_source_dataframe(
        self, df_source: pd.DataFrame
    ) -> List[ResultLocation]:
        """Generate a list of ResultLocation objects based on the source DataFrame."""
        tsids = TimeSeriesId.from_multiindex(df_source.columns)
        result_locations = [t.to_result_quantity(self.res1d).result_location for t in tsids]
        return result_locations

    def _create_time_series_id_from_source(self, source: TimeSeriesId) -> TimeSeriesId:
        """Create a TimeSeriesId for the derived quantity based on the source quantity TimeSeriesId."""
        derived_tsid = replace(source, quantity=self.name, derived=True)
        return derived_tsid

    def _create_time_series_ids_from_source(
        self, source_timeseries_ids: List[TimeSeriesId]
    ) -> List[TimeSeriesId]:
        """Create a list of TimeSeriesId for the derived quantity based on a list of source quantity TimeSeriesId objects."""
        derived_tsids = [
            self._create_time_series_id_from_source(tsid) for tsid in source_timeseries_ids
        ]
        return derived_tsids

    def _create_derived_columns(self, df_columns: pd.MultiIndex) -> pd.MultiIndex:
        """Create a column index for the derived quantity based on the source quantity's DataFrame.columns."""
        source_tsids = TimeSeriesId.from_multiindex(df_columns)
        derived_tsids = self._create_time_series_ids_from_source(source_tsids)
        derived_columns = TimeSeriesId.to_multiindex(derived_tsids)
        return derived_columns

    def _get_source_timeseries_ids_for_locations(
        self, result_locations: ResultLocations
    ) -> List[TimeSeriesId]:
        """Generate a list of TimeSeriesId for the source quantity for a particular ResultLocations object."""
        if result_locations.group not in self.groups:
            return []
        if self.source_quantity not in result_locations.quantities:
            return []

        quantity_collection = result_locations.quantities[self.source_quantity]
        tsids = quantity_collection.get_timeseries_ids()
        return tsids

    def _get_source_timeseries_ids_for_location(
        self, result_location: ResultLocation
    ) -> List[TimeSeriesId]:
        """Generate a list of TimeSeriesId for the source quantity for a particular ResultLocation object."""
        if result_location.group not in self.groups:
            return []
        if self.source_quantity not in result_location.quantities:
            return []

        result_quantities = result_location._creator.result_quantity_map[self.source_quantity]
        tsids = [q.timeseries_id for q in result_quantities]
        return tsids
