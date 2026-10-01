"""Module for the ResultQuantityDerived class."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import NoReturn

if TYPE_CHECKING:  # pragma: no cover
    from .result_location import ResultLocation
    from ..res1d import Res1D

    import pandas as pd
    from matplotlib.axes import Axes

from ..quantities import DerivedQuantity


class ResultQuantityDerived:
    """Class for a derived quantity that can be read and plotted."""

    def __init__(
        self,
        derived_quantity: DerivedQuantity,
        result_location: ResultLocation,
        res1d: Res1D,
    ):
        self.derived_quantity = derived_quantity
        self.result_location = result_location
        self.res1d: Res1D = res1d

    def __repr__(self) -> str:
        """Return a string representation of the object.

        Returns
        -------
        str
            The name of the derived quantity.

        """
        return f"<DerivedQuantity: {self.name}>"

    @property
    def name(self) -> str:
        """Return the name of the derived quantity."""
        return self.derived_quantity.name

    def add(self) -> NoReturn:
        """Add a ResultQuantity to ResultNetwork.read_queue."""
        raise NotImplementedError("Derived quantities cannot be added to a network.")

    def read(self, column_mode: str | None = None) -> pd.DataFrame:
        """Read the time series data into a data frame.

        Parameters
        ----------
        column_mode : str (optional)
            Specifies the type of column index of returned DataFrame.
            'all' - column MultiIndex with levels matching TimeSeriesId objects.
            'compact' - same as 'all', but removes levels with default values.
            'timeseries' - column index of TimeSeriesId objects
            'str' - column index of str representations of QueryData objects

        Returns
        -------
        pd.DataFrame
            Time series data of the derived quantity.

        """
        df_source = self._create_source_dataframe()
        df_derived = self.derived_quantity.generate(df_source)
        return df_derived.droplevel("derived", axis=1)

    def to_dataframe(self, column_mode: str | None = None) -> pd.DataFrame:
        """Read the time series data into a data frame.

        Alias for read() method.

        Parameters
        ----------
        column_mode : str (optional)
            Specifies the type of column index of returned DataFrame.
            'all' - column MultiIndex with levels matching TimeSeriesId objects.
            'compact' - same as 'all', but removes levels with default values.
            'timeseries' - column index of TimeSeriesId objects
            'str' - column index of str representations of QueryData objects

        Returns
        -------
        pd.DataFrame
            Time series data of the derived quantity.

        """
        return self.read(column_mode)

    def plot(self, ax: Axes | None = None, **kwargs) -> Axes:
        """Plot the time series data.

        Parameters
        ----------
        ax : matplotlib.axes.Axes, optional
            Axes object to plot on.
        **kwargs
            Additional keyword arguments passed to pandas.DataFrame.plot.

        Returns
        -------
        matplotlib.axes.Axes
            Axes object with the plot.
        """
        df = self.read()
        ax = df.plot(ax=ax, **kwargs)
        ax.set_xlabel("Time")
        ax.set_ylabel(f"{self.derived_quantity.name}")
        ax.grid(True)
        return ax

    def _create_source_dataframe(self) -> pd.DataFrame:
        """Create the source DataFrame used to calculate the derived quantity.

        Returns
        -------
        pd.DataFrame
            Time series of the source quantity at this location.

        """
        return self.derived_quantity.create_source_dataframe_for_location(self.result_location)
