"""Module for the ResultQuantityDerived class."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from typing import Optional

    from .result_location import ResultLocation
    from ..res1d import Res1D
    from ..result_reader_writer.result_reader import ColumnMode

    import pandas as pd

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
        """Return a string representation of the object."""
        return f"<DerivedQuantity: {self.name}>"

    @property
    def name(self) -> str:
        """Return the name of the derived quantity."""
        return self.derived_quantity.name

    def add(self):
        """Add a ResultQuantity to ResultNetwork.read_queue."""
        raise NotImplementedError("Derived quantities cannot be added to a network.")

    def read(self, column_mode: Optional[str | ColumnMode] = None) -> pd.DataFrame:
        """Read the time series data into a data frame.

        Parameters
        ----------
        column_mode : str | ColumnMode (optional)
            Specifies the type of column index of returned DataFrame.
            'all' - column MultiIndex with levels matching TimeSeriesId objects.
            'compact' - same as 'all', but removes levels with default values.
            'timeseries' - column index of TimeSeriesId objects
            'str' - column index of str representations of QueryData objects

        """
        df_source = self._create_source_dataframe()
        df_derived = self.derived_quantity.generate(df_source)
        return df_derived.droplevel("derived", axis=1)

    def plot(self, ax=None, **kwargs):
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
        """Create the source DataFrame used to calculate the derived quantity."""
        return self.derived_quantity.create_source_dataframe_for_location(self.result_location)
