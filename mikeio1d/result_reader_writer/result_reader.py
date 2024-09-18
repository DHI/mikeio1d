from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from typing import List
    from typing import Optional

import warnings

from enum import Enum
from abc import ABC
from abc import abstractmethod

import os.path
import pandas as pd
import datetime

from ..dotnet import from_dotnet_datetime
from ..various import NAME_DELIMITER
from ..quantities import TimeSeriesId

from DHI.Mike1D.ResultDataAccess import ResultData
from DHI.Mike1D.ResultDataAccess import ResultDataQuery
from DHI.Mike1D.ResultDataAccess import ResultDataSearch
from DHI.Mike1D.ResultDataAccess import Filter
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
    """
    Class for reading the ResultData object TimeData
    into Pandas data frame.

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
        lazy_load=False,
        header_load=False,
        reaches=None,
        nodes=None,
        catchments=None,
        col_name_delimiter=NAME_DELIMITER,
        put_chainage_in_col_name=True,
    ):
        self.res1d = res1d

        self.file_path = file_path
        self.file_extension = os.path.splitext(file_path)[-1]

        self.lazy_load = lazy_load

        self._reaches = reaches if reaches else []
        self._nodes = nodes if nodes else []
        self._catchments = catchments if catchments else []

        self.use_filter = reaches is not None or nodes is not None or catchments is not None

        self._load_header()
        if not header_load:
            self._load_file()

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

        if self.use_filter:
            self.data.LoadHeader(True, self.diagnostics)
        else:
            self.data.LoadHeader(self.diagnostics)

    def _load_file(self):
        if self.use_filter:
            self._setup_filter()

            for reach in self._reaches:
                self._add_reach(reach)
            for node in self._nodes:
                self._add_node(node)
            for catchment in self._catchments:
                self._add_catchment(catchment)

        if self.file_extension.lower() in [".resx", ".crf", ".prf", ".xrf"]:
            self.data.Load(self.diagnostics)
        else:
            self.data.LoadData(self.diagnostics)

        self.query = ResultDataQuery(self.data)
        self.searcher = ResultDataSearch(self.data)

    def _setup_filter(self):
        """
        Setup the filter for result data object.
        """
        if not self.use_filter:
            return

        self.data_filter = Filter()
        self.data_subfilter = DataItemFilterName(self.data)
        self.data_filter.AddDataItemFilter(self.data_subfilter)

        self.data.Parameters.Filter = self.data_filter

    def _add_reach(self, reach_id):
        self.data_subfilter.Reaches.Add(reach_id)

    def _add_node(self, node_id):
        self.data_subfilter.Nodes.Add(node_id)

    def _add_catchment(self, catchment_id):
        self.data_subfilter.Catchments.Add(catchment_id)

    # endregion File loading

    @abstractmethod
    def read(
        self,
        timeseries_ids: List[TimeSeriesId] = None,
        column_mode: Optional[str | ColumnMode] = None,
    ) -> pd.DataFrame:
        """
        Read the time series data into a data frame.

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
        """
        Read all time series data into a data frame.

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
        """Skip filtered data sets"""
        name = self.get_data_set_name(data_set)
        if self.use_filter and name not in self._catchments + self._reaches + self._nodes:
            return False
        return True

    @property
    def time_index(self):
        """pandas.DatetimeIndex of the time index."""
        if self._time_index is not None:
            return self._time_index

        if self.is_lts_result_file():
            return self.lts_event_index

        time_stamps = [from_dotnet_datetime(t) for t in self.data.TimesList]
        self._time_index = pd.DatetimeIndex(time_stamps)
        return self._time_index

    def get_data_set_name(self, data_set, item_id=None):
        name = TimeSeriesId.get_dataset_name(data_set, item_id, self.col_name_delimiter)
        return name

    def get_column_name(self, data_set, data_item, i):
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
        """Determines if the quantity_column is the LTS event time column.

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
        # For pythonnet version > 3.0 it is possible to call
        # return self._data.ResultType.Equals(ResultTypes.LTSEvents)
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
