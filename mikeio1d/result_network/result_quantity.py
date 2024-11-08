"""Module for ResultQuantity class."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from typing import Optional
    from ..res1d import Res1D
    from ..result_network import ResultLocation
    from ..result_reader_writer.result_reader import ColumnMode

    import pandas as pd

from .data_entry import DataEntry
from ..quantities import TimeSeriesId
from ..result_query import QueryDataCreator

from DHI.Mike1D.MikeIO import DataEntry as DataEntryNet
from DHI.Mike1D.Generic import IQuantity


class ResultQuantity:
    """Class for wrapping a single ResultData data item quantity.

    ResultQuantity objects are the last attributes assigned to a network.
    They have the ability to add a query.

    Parameters
    ----------
    result_location: ResultLocation
        ResultLocation object, which could be node, catchment, grid point, or global data item.
    data_item: IDataItem
        MIKE 1D IDataItem object.
    res1d : Res1D
        Res1D object the quantity belongs to.
    m1d_dataset: IRes1DDataSet, optional
        IRes1DDataSet object the quantity is associated with.

    Attributes
    ----------
    element_index : int
        An integer giving an element index into the data item
        which gives the concrete time series for given location.
    timeseries_id : TimeSeriesId
        A unique TimeSeriesId object corresponding to the data item. This is
        unmutable and set when the ResultQuantity is added to a network. A value
        of None indicates that the ResultQuantity has not been added to a network.

    """

    def __init__(
        self,
        result_location: ResultLocation,
        data_item,
        res1d: Res1D,
        m1d_dataset=None,
        element_index=0,
    ):
        self.result_location = result_location
        self.data_item = data_item
        self.res1d: Res1D = res1d
        self.m1d_dataset = m1d_dataset
        self.element_index = element_index
        self._timeseries_id: TimeSeriesId = None
        self._name = data_item.Quantity.Id

    def __repr__(self) -> str:
        """Return a string representation of the object."""
        return f"<Quantity: {ResultQuantity.prettify_quantity(self)}>"

    @staticmethod
    def prettify_quantity(quantity: ResultQuantity | IQuantity, latex_format=False) -> str:
        """Get a pretty string representation of a ResultQuantity's type and unit.

        Parameters
        ----------
        quantity: ResultQuantity | IQuantity
            ResultQuantity object or DHI.Mike1D.Generic.IQuantity object.
        latex_format: bool, optional
            If True, the unit abbreviation will use LaTeX-formatted text.

        Returns
        -------
        str
            A string representation of the quantity type and unit.

        """
        if isinstance(quantity, ResultQuantity):
            m1d_quantity = quantity.data_item.Quantity
        elif isinstance(quantity, IQuantity):
            m1d_quantity = quantity
        else:
            raise ValueError(
                f"quantity must be a ResultQuantity or IQuantity object. Got {type(quantity)}."
            )

        description = m1d_quantity.Description
        unit_abbreviation = m1d_quantity.EumQuantity.UnitAbbreviation
        if latex_format:
            unit_abbreviation = f"$\\mathrm{{{unit_abbreviation}}}$"
        return f"{description} ({unit_abbreviation})"

    @property
    def name(self) -> str:
        """Name of the quantity id assosciated with collection."""
        return self._name

    def add(self):
        """Add a ResultQuantity to ResultNetwork.read_queue based on the data item."""
        self.res1d.network.queue.append(self.timeseries_id)

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
        return self.res1d.read(self.timeseries_id, column_mode=column_mode)

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
        ax.set_ylabel(ResultQuantity.prettify_quantity(self, latex_format=True))
        ax.grid(True)
        return ax

    def to_dataframe(self):
        """Get a time series as a data frame."""
        return self.read()

    def to_csv(self, file_path, time_step_skipping_number=1):
        """Extract time series data into a csv file."""
        query = self.get_query()
        self.res1d.to_csv(file_path, query, time_step_skipping_number)

    def to_dfs0(self, file_path, time_step_skipping_number=1):
        """Extract time series data into a dfs0 file."""
        query = self.get_query()
        self.res1d.to_dfs0(file_path, query, time_step_skipping_number)

    def to_txt(self, file_path, time_step_skipping_number=1):
        """Extract time series data into a txt file."""
        query = self.get_query()
        self.res1d.to_txt(file_path, query, time_step_skipping_number)

    def get_query(self):
        """Get query corresponding to ResultQuantity."""
        return QueryDataCreator.from_timeseries_id(self._timeseries_id)

    def get_data_entry(self):
        """Get DataEntry corresponding to ResultQuantity."""
        return DataEntry(self.data_item, self.element_index, self.m1d_dataset)

    def get_data_entry_net(self):
        """Get DataEntryNet corresponding to ResultQuantity."""
        return DataEntryNet(self.data_item, self.element_index)

    @property
    def timeseries_id(self) -> TimeSeriesId:
        """TimeSeriesId corresponding to ResultQuantity."""
        if self._timeseries_id is None:
            message = "ResultQuantity must be added to a ResultNetwork before TimeSeriesId can be accessed."
            ValueError(message)
        return self._timeseries_id
