from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Optional
    from ..result_reader_writer.result_reader import ColumnMode

    import pandas as pd

from .result_quantity import ResultQuantity


class ResultQuantityCollection(ResultQuantity):
    """
    Class for dealing with a collection ResultQuantity objects.

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

    def __init__(self, result_quantities, res1d):
        self.result_quantities = result_quantities
        self.res1d = res1d

    def __repr__(self) -> str:
        return f"<QuantityCollection ({len(self.result_quantities)}): {self.name}>"

    @property
    def name(self) -> str:
        """Name of the quantity id assosciated with collection."""
        if len(self.result_quantities) <= 0:
            return "EMPTY"
        return self.result_quantities[0].name

    def add(self):
        """
        Add queries to ResultNetwork.queries from a list of result quantities.
        """
        for result_quantity in self.result_quantities:
            result_quantity.add()

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
        timeseries_ids = [q.timeseries_id for q in self.result_quantities]
        return self.res1d.read(timeseries_ids, column_mode=column_mode)

    def plot(self, **kwargs):
        """Plot the time series data."""
        if len(self.result_quantities) <= 0:
            return

        # Taking the first data item is enough, because all of them have
        # the same quantity and for plotting.
        self.data_item = self.result_quantities[0].data_item
        return ResultQuantity.plot(self, **kwargs)

    def get_query(self):
        """Get queries corresponding to ResultQuantityCollection."""
        queries = []
        for result_quantity in self.result_quantities:
            query = result_quantity.get_query()
            queries.append(query)
        return queries
