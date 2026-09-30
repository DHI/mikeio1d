"""Module for ResultQuantityCollection class."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from ..res1d import Res1D
    from ..quantities import TimeSeriesId
    from ..result_query import QueryData

    import pandas as pd
    from matplotlib.axes import Axes

from .result_quantity import ResultQuantity


class ResultQuantityCollection(ResultQuantity):
    """Class for dealing with a collection ResultQuantity objects.

    ResultQuantityCollection objects are the attributes assigned to a network
    type like nodes, catchments, etc. For example, res1d.nodes.WaterLevel
    They have the ability to add queries.

    Parameters
    ----------
    result_quantities: list of ResultQuantity objects
        A list of ResultQuantity objects having the same quantity id.
    res1d : Res1D
        Res1D object the quantity belongs to.

    """

    def __init__(self, result_quantities: list[ResultQuantity], res1d: Res1D):
        self.result_quantities = result_quantities
        self.res1d = res1d

    def __repr__(self) -> str:
        """Return a string representation of the object.

        Returns
        -------
        str
            The number of quantities in the collection and the quantity's name.

        """
        pretty_quantity = ResultQuantity.prettify_quantity(self.result_quantities[0])
        return f"<QuantityCollection ({len(self.result_quantities)}): {pretty_quantity}>"

    @property
    def name(self) -> str:
        """Name of the quantity id assosciated with collection."""
        if len(self.result_quantities) <= 0:
            return "EMPTY"
        return self.result_quantities[0].name

    def add(self) -> None:
        """Add queries to ResultNetwork.queries from a list of result quantities."""
        for result_quantity in self.result_quantities:
            result_quantity.add()

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
            Time series data of every quantity in the collection.

        """
        timeseries_ids = [q.timeseries_id for q in self.result_quantities]
        return self.res1d.read(timeseries_ids, column_mode=column_mode)

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
            Time series data of every quantity in the collection.

        """
        return self.read(column_mode)

    def plot(self, ax: Axes | None = None, **kwargs) -> Axes | None:
        """Plot the time series data.

        Parameters
        ----------
        ax : matplotlib.axes.Axes, optional
            Axes object to plot on.
        **kwargs
            Additional keyword arguments passed to pandas.DataFrame.plot.

        Returns
        -------
        matplotlib.axes.Axes or None
            Axes object with the plot, or None if the collection is empty.
        """
        if len(self.result_quantities) <= 0:
            return

        # Taking the first data item is enough, because all of them have
        # the same quantity and for plotting.
        self.data_item = self.result_quantities[0].data_item
        return ResultQuantity.plot(self, ax=ax, **kwargs)

    def get_timeseries_ids(self) -> list[TimeSeriesId]:
        """Get TimeSeriesId objects corresponding to ResultQuantityCollection.

        Returns
        -------
        list[TimeSeriesId]
            One TimeSeriesId per quantity in the collection.

        """
        timeseries_ids = [q.timeseries_id for q in self.result_quantities]
        return timeseries_ids

    def get_query(self) -> list[QueryData]:
        """Get queries corresponding to ResultQuantityCollection.

        Returns
        -------
        list[QueryData]
            One query per quantity in the collection.

        """
        queries = []
        for result_quantity in self.result_quantities:
            query = result_quantity.get_query()
            queries.append(query)
        return queries
