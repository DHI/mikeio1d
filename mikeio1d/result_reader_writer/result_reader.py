import os.path
import pandas as pd
import datetime

from ..dotnet import from_dotnet_datetime
from ..various import NAME_DELIMITER

from DHI.Mike1D.ResultDataAccess import ResultData
from DHI.Mike1D.ResultDataAccess import ResultDataQuery
from DHI.Mike1D.ResultDataAccess import ResultDataSearch
from DHI.Mike1D.ResultDataAccess import Filter
from DHI.Mike1D.ResultDataAccess import DataItemFilterName
from DHI.Mike1D.ResultDataAccess import ResultTypes

from DHI.Mike1D.Generic import Connection
from DHI.Mike1D.Generic import Diagnostics


class ResultReader:
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

    def __init__(self,
                 res1d,
                 file_path=None,
                 lazy_load=False,
                 header_load=False,
                 reaches=None,
                 nodes=None,
                 catchments=None,
                 col_name_delimiter=NAME_DELIMITER,
                 put_chainage_in_col_name=True):

        self.res1d = res1d

        self.file_path = file_path
        self.file_extension = os.path.splitext(file_path)[-1]

        self.lazy_load = lazy_load

        self._reaches = reaches if reaches else []
        self._nodes = nodes if nodes else []
        self._catchments = catchments if catchments else []

        self.use_filter = (reaches is not None or
                           nodes is not None or
                           catchments is not None)

        self._load_header()
        if not header_load:
            self._load_file()

        self._time_index = None

        self.col_name_delimiter = col_name_delimiter
        self.put_chainage_in_col_name = put_chainage_in_col_name

        self.quantities = [quantity.Id for quantity in self.data.Quantities]

    #region File loading

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

        if self.file_extension.lower() in ['.resx', '.crf', '.prf', '.xrf']:
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

    #endregion File loading

    def read(self, queries=None):
        return None

    def read_all(self):
        return None

    def is_data_set_included(self, data_set):
        """ Skip filtered data sets """
        name = self.get_data_set_name(data_set)
        if self.use_filter and name not in self._catchments + self._reaches + self._nodes:
            return False
        return True

    @property
    def time_index(self):
        """ pandas.DatetimeIndex of the time index. """
        if self._time_index is not None:
            return self._time_index

        if self.is_lts_result_file():
            return self.lts_event_index

        time_stamps = [from_dotnet_datetime(t) for t in self.data.TimesList]
        self._time_index = pd.DatetimeIndex(time_stamps)
        return self._time_index

    def get_data_set_name(self, data_set, item_id=None):
        name = None

        if hasattr(data_set, "Name"):
            name = data_set.Name
        elif hasattr(data_set, "Id"):
            name = data_set.Id
        elif data_set.Quantity is not None:
            name = data_set.Quantity.Id

        name = "" if name is None else name

        # Add item id if present before the name.
        # Needed for unique identification of structures.
        name = self.col_name_delimiter.join([item_id, name]) if item_id is not None else name

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

    #region Methods for LTS result files

    def update_time_quantities(self, df):
        if not self.is_lts_result_file():
            return

        simulation_start = from_dotnet_datetime(self.data.StartTime)
        for label in df:
            time_suffix = f'Time{self.col_name_delimiter}'
            if time_suffix in label:
                seconds_after_simulation_start_array = df[label].to_numpy()
                times = [
                    simulation_start + datetime.timedelta(seconds=float(sec)) for sec in seconds_after_simulation_start_array
                ]
                df[label] = times

    def is_lts_result_file(self):
        # For pythonnet version > 3.0 it is possible to call
        # return self._data.ResultType.Equals(ResultTypes.LTSEvents)
        return int(self.data.ResultType) == int(ResultTypes.LTSEvents)

    @property
    def lts_event_index(self):
        """ pandas.DatetimeIndex of the LTS event index. """
        if self._time_index is not None:
            return self._time_index

        number_of_event_entries = len(self.data.TimesList)
        event_index = [i for i in range(number_of_event_entries)]

        self._time_index = pd.Index(event_index)

        return self._time_index

    #endregion Methods for LTS result files
