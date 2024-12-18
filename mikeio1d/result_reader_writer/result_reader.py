"""Module for ResultReader class."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from typing import List
    from typing import Optional
    from ..res1d import Res1D
    from ..filter import ResultFilter

import warnings

from enum import Enum
from abc import ABC
from abc import abstractmethod

import os.path
import pandas as pd
import datetime

from ..dotnet import from_dotnet_datetime
from ..dotnet import pythonnet_implementation as impl
from ..various import NAME_DELIMITER
from ..quantities import TimeSeriesId
from ..result_network import ResultNetwork

from DHI.Mike1D.ResultDataAccess import ResultData
from DHI.Mike1D.ResultDataAccess import ResultDataQuery
from DHI.Mike1D.ResultDataAccess import ResultDataSearch
from DHI.Mike1D.ResultDataAccess import DataItemFilterName
from DHI.Mike1D.ResultDataAccess import ResultTypes

from DHI.Mike1D.Generic import Connection
from DHI.Mike1D.Generic import Diagnostics


class ColumnMode(str, Enum):
    """Specifies the type of column index of returned DataFrames."""

    ALL = "all"
    """Uses a column MultiIndex with all possible metadata."""
    COMPACT = "compact"
    """Uses a column MultiIndex with only the relevant metadata."""
    TIMESERIES = "timeseries"
    """Uses a column Index with headers as TimeSeriesId objects"""
    STRING = "str"
    """Uses a column Index with headers as the string representation of QueryData objects."""


class ResultReader(ABC):
    """Class for reading the ResultData object TimeData into Pandas data frame.

    Parameters
    ----------
    res1d : Res1D
        Res1D object the modified ResultData belongs to.
    file_path : str
        Relative or absolute path of the relevant result file.
    lazy_load : bool
        Flag specifying to load the file using lazy loading bridge of MIKE 1D.
        This typically is useful if only a few time steps need to be read for the whole network.
    header_load : bool
        Flag specifying to load just a header of the result file.
    reaches : list of str
        Filter list of reach ID strings, which will be included when loading the result file.
    nodes : list of str
        Filter list of node ID strings, which will be included when loading the result file.
    catchments : list of str
        Filter list of catchment ID strings, which will be included when loading the result file.
    col_name_delimiter : str
        String to delimit the quantity ID with location ID
        (and optionally chainage) in the data frame label.
    put_chainage_in_col_name : bool
        Flag specifying to add chainage into data frame column label.

    """

    def __init__(
        self,
        res1d,
        file_path=None,
        col_name_delimiter=NAME_DELIMITER,
        put_chainage_in_col_name=True,
        filter: ResultFilter = None,
    ):
        self.res1d: Res1D = res1d

        self.file_path = file_path
        self.file_extension = os.path.splitext(file_path)[-1]

        self.lazy_load = False

        self.filter = filter
        self._loaded = False

        self._load_header()

        self._time_index = None

        self.col_name_delimiter = col_name_delimiter
        self.put_chainage_in_col_name = put_chainage_in_col_name

        self.quantities = [quantity.Id for quantity in self.data.Quantities]

        self.column_mode: ColumnMode = ColumnMode.STRING
        """Specifies the type of column index of returned DataFrames.
        
        'all' - Uses a column MultiIndex with all possible metadata
        'compact' - Uses a column MultiIndex with only the relevant metadata
        'timeseries' - Uses a column Index with headers as TimeSeriesId objects
        'str' - Uses a column Index with headers as the string representation of QueryData objects
        """

    # region File loading

    def _load_header(self):
        if not os.path.exists(self.file_path):
            raise FileExistsError(f"File {self.file_path} does not exist.")

        self.data = ResultData()
        self.data.Connection = Connection.Create(self.file_path)
        self.diagnostics = Diagnostics("Loading header")

        if self.lazy_load:
            self.data.Connection.BridgeName = "res1dlazy"

        if self.filter.use_filter():
            self.data.LoadHeader(True, self.diagnostics)
        else:
            self.data.LoadHeader(self.diagnostics)

        # IMPORTANT: The filter must be applied after the header is loaded. Applying the filter before loading the header
        #            causes unexpected results due to a bug in MIKE 1D.
        self.filter.apply(self.data)

    def _load_file(self):
        if self.file_extension.lower() in [".resx", ".crf", ".prf", ".xrf"]:
            self.data.Load(self.diagnostics)
            # required since ResultData.Load() creates new network objects, invalidating ResultNetwork references
            self.res1d.network = ResultNetwork(self.res1d)
        else:
            self.data.LoadData(self.diagnostics)

    def load_dynamic_data(self):
        """Load the dynamic data from the file if it has not already  been loaded."""
        if not self._loaded:
            self._load_file()
            self._loaded = True

    # endregion File loading

    @abstractmethod
    def read(
        self,
        timeseries_ids: List[TimeSeriesId] = None,
        column_mode: Optional[str | ColumnMode] = None,
    ) -> pd.DataFrame:
        """Read the time series data into a data frame.

        Parameters
        ----------
        timeseries_ids : list of TimeSeriesId
            List of TimeSeriesId objects to read.
            If None, all data sets will be read.
        column_mode : str | ColumnMode (optional)
            Specifies the type of column index of returned DataFrame.

        Returns
        -------
        pd.DataFrame

        """
        ...

    @abstractmethod
    def read_all(self, column_mode: Optional[str | ColumnMode]) -> pd.DataFrame:
        """Read all time series data into a data frame.

        Parameters
        ----------
        column_mode : str | ColumnMode (optional)
            Specifies the type of column index of returned DataFrame.

        Returns
        -------
        pd.DataFrame

        """
        ...

    def is_data_set_included(self, data_set):
        """Skip filtered data sets."""
        if not self.filter.use_filter():
            return True

        m1d_filter = self.filter.res1d_filter
        for data_item in data_set.DataItems:
            if m1d_filter.Include(data_item):
                return True
        return False

    @property
    def query(self):
        """For querying the result data."""
        if not self._loaded:
            self.load_dynamic_data()
        if not hasattr(self, "_query"):
            self._query = ResultDataQuery(self.data)
        return self._query

    @property
    def searcher(self):
        """For searching the result data."""
        if not self._loaded:
            self.load_dynamic_data()
        if not hasattr(self, "_searcher"):
            self._searcher = ResultDataSearch(self.data)
        return self._searcher

    @property
    def time_index(self):
        """pandas.DatetimeIndex of the time index."""
        self.load_dynamic_data()

        if self._time_index is not None:
            return self._time_index

        if self.is_lts_result_file():
            return self.lts_event_index

        time_stamps = [from_dotnet_datetime(t) for t in self.data.TimesList]
        self._time_index = pd.DatetimeIndex(time_stamps)
        return self._time_index

    def get_data_set_name(self, data_set, item_id=None):
        """Get the name of the data set."""
        name = TimeSeriesId.get_dataset_name(data_set, item_id, self.col_name_delimiter)
        return name

    def get_column_name(self, data_set, data_item, i):
        """Get the column name for the data frame."""
        quantity_id = data_item.Quantity.Id
        item_id = data_item.ItemId
        name = self.get_data_set_name(data_set, item_id)

        chainage = None
        if data_item.IndexList is not None:
            chainages = data_set.GetChainages(data_item)
            chainage = chainages[i]

        if name == "":
            return quantity_id

        if chainage is None:
            return self.col_name_delimiter.join([quantity_id, name])

        postfix = f"{chainage:g}" if self.put_chainage_in_col_name else str(i)
        return self.col_name_delimiter.join([quantity_id, name, postfix])

    # region Methods for LTS result files

    def update_time_quantities(self, df: pd.DataFrame):
        """Update the time quantities in the data frame to datetime objects."""
        if not self.is_lts_result_file():
            return

        simulation_start = from_dotnet_datetime(self.data.StartTime)

        column_level_names = None
        if isinstance(df.columns, pd.MultiIndex):
            column_level_names = df.columns.names

        # Loop over all columns by number and update them by number as well.
        for i in range(len(df.columns)):
            if not self._is_lts_event_time_column(
                df.columns[i], column_level_names=column_level_names
            ):
                continue

            seconds_since_simulation_started = df.iloc[:, i]
            datetime_since_simulation_started = [
                simulation_start + datetime.timedelta(seconds=s)
                for s in seconds_since_simulation_started
            ]

            # Suppress casting warning for now with hope that it will be fixed by pandas in the future.
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", category=FutureWarning)
                df.iloc[:, i] = datetime_since_simulation_started

    def _is_lts_event_time_column(
        self,
        quantity_column: str | TimeSeriesId | tuple,
        column_level_names: Optional[List[str]] = None,
    ) -> bool:
        """Determine if the quantity_column is the LTS event time column.

        Parameters
        ----------
        quantity_column : str | TimeSeriesId | tuple
            The column header containing the event statistic quantities.
        column_level_names : list of str, optional
            The column level names of the data frame, by default None.
            Only used if the data frame has a MultiIndex column index.

        """
        if isinstance(quantity_column, str):
            time_suffix = f"Time{self.col_name_delimiter}"
            return time_suffix in quantity_column
        elif isinstance(quantity_column, TimeSeriesId):
            quantity = quantity_column.quantity
            return quantity.endswith("Time")
        elif isinstance(quantity_column, tuple):
            tsid = TimeSeriesId.from_tuple(quantity_column, column_level_names=column_level_names)
            quantity = tsid.quantity
            return quantity.endswith("Time")
        else:
            raise TypeError(f"Unsupported type {type(quantity_column)} for quantity_column.")

    def is_lts_result_file(self):
        """Check if the result file is an LTS result file.

        Notes
        -----
        For pythonnet version > 3.0 it is possible to call
        return self._data.ResultType.Equals(ResultTypes.LTSEvents)
        """
        return int(self.data.ResultType) == int(ResultTypes.LTSEvents)

    @property
    def lts_event_index(self):
        """pandas.DatetimeIndex of the LTS event index."""
        if self._time_index is not None:
            return self._time_index

        number_of_event_entries = len(self.data.TimesList)
        event_index = [i for i in range(number_of_event_entries)]

        self._time_index = pd.Index(event_index)

        return self._time_index

    # endregion Methods for LTS result files

    @property
    def bridge(self):
        """The bridge object for the result data."""
        return impl(self.data.Bridge)

    @property
    def number_of_time_steps(self):
        """Number of time steps in the result data."""
        return self.bridge.NumberOfTimeSteps
