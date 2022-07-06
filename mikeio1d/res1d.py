import os.path
import pandas as pd

from .dotnet import from_dotnet_datetime
from .dotnet import to_dotnet_datetime
from .dotnet import to_numpy
from .dotnet import pythonnet_implementation as impl

from .query import QueryData
from .query import QueryDataCatchment
from .query import QueryDataNode
from .query import QueryDataReach

from .various import mike1d_quantities
from .various import NAME_DELIMITER

from System import DateTime

from DHI.Mike1D.ResultDataAccess import ResultData
from DHI.Mike1D.ResultDataAccess import ResultDataQuery
from DHI.Mike1D.ResultDataAccess import Filter
from DHI.Mike1D.ResultDataAccess import DataItemFilterName

from DHI.Mike1D.Generic import Connection
from DHI.Mike1D.Generic import Diagnostics


class Res1D:

    def __init__(self,
                 file_path=None,
                 lazy_load=False,
                 header_load=False,
                 reaches=None,
                 nodes=None,
                 catchments=None,
                 col_name_delimiter=NAME_DELIMITER,
                 put_chainage_in_col_name=True):

        self.file_path = file_path
        self._lazy_load = lazy_load

        self._reaches = reaches if reaches else []
        self._nodes = nodes if nodes else []
        self._catchments = catchments if catchments else []

        self._use_filter = (reaches is not None or
                            nodes is not None or
                            catchments is not None)

        self._time_index = None
        self._start_time = None
        self._end_time = None

        self._queries = []

        self._load_header()
        if not header_load:
            self._load_file()

        self._col_name_delimiter = col_name_delimiter
        self._put_chainage_in_col_name = put_chainage_in_col_name

    def __repr__(self):
        out = ["<mikeio1d.Res1D>"]

        if self.file_path:
            out.append(f"Start time: {str(self.start_time)}")
            out.append(f"End time: {str(self.end_time)}")
            out.append(f"# Timesteps: {str(self.data.NumberOfTimeSteps)}")
            out.append(f"# Catchments: {self.data.Catchments.get_Count()}")
            out.append(f"# Nodes: {self.data.Nodes.get_Count()}")
            out.append(f"# Reaches: {self.data.Reaches.get_Count()}")

            out.append(f"# Globals: {self.data.GlobalData.DataItems.Count}")
            for i, quantity in enumerate(self.data.Quantities):
                out.append(f"{i} - {quantity.Id} <{quantity.EumQuantity.UnitAbbreviation}>")

        return str.join("\n", out)

    #region File loading

    def _load_header(self):
        if not os.path.exists(self.file_path):
            raise FileExistsError(f"File {self.file_path} does not exist.")

        self._data = ResultData()
        self._data.Connection = Connection.Create(self.file_path)
        self._diagnostics = Diagnostics("Loading header")

        if self._lazy_load:
            self._data.Connection.BridgeName = "res1dlazy"

        if self._use_filter:
            self._data.LoadHeader(True, self._diagnostics)
        else:
            self._data.LoadHeader(self._diagnostics)

    def _load_file(self):

        if self._use_filter:
            self._setup_filter()

            for reach in self._reaches:
                self._add_reach(reach)
            for node in self._nodes:
                self._add_node(node)
            for catchment in self._catchments:
                self._add_catchment(catchment)

            self._data.LoadData(self._diagnostics)
        else:
            self._data.Load(self._diagnostics)

        self._query = ResultDataQuery(self._data)

    def _setup_filter(self):
        """
        Setup the filter for result data object.
        """
        if not self._use_filter:
            return

        self._data_filter = Filter()
        self._data_subfilter = DataItemFilterName(self._data)
        self._data_filter.AddDataItemFilter(self._data_subfilter)

        self._data.Parameters.Filter = self._data_filter

    def _add_reach(self, reach_id):
        self._data_subfilter.Reaches.Add(reach_id)

    def _add_node(self, node_id):
        self._data_subfilter.Nodes.Add(node_id)

    def _add_catchment(self, catchment_id):
        self._data_subfilter.Catchments.Add(catchment_id)

    #endregion File loading

    def read(self, queries=None):
        """
        Read loaded .res1d file data.

        Parameters
        ----------
        queries: A single query or a list of queries.
        Default is None = reads all data.
        """

        if queries is None:
            return self.read_all()

        queries = queries if isinstance(queries, list) else [queries]

        dfs = []
        for query in queries:
            df = pd.DataFrame(index=self.time_index)
            df[str(query)] = query.get_values(self)
            dfs.append(df)

        return pd.concat(dfs, axis=1)

    def read_all(self):
        """ Read all data from res1d file to dataframe. """

        dfs = []
        for data_set in self.data.DataSets:

            data_set = impl(data_set)

            # Skip filtered data sets
            name = Res1D.get_data_set_name(data_set)
            if self._use_filter and name not in self._catchments + self._reaches + self._nodes:
                continue

            for data_item in data_set.DataItems:
                values_name_pair = self.get_values(data_set, data_item)

                for values, col_name in values_name_pair:
                    df = pd.DataFrame(index=self.time_index)
                    df[col_name] = values
                    dfs.append(df)

        return pd.concat(dfs, axis=1)

    def get_values(self, data_set, data_item):
        """ Get all time series values in given data_item. """
        if data_item.IndexList is None:
            return self.get_scalar_value(data_set, data_item)
        else:
            return self.get_vector_values(data_set, data_item)

    def get_scalar_value(self, data_set, data_item):
        name = Res1D.get_data_set_name(data_set)
        quantity_id = data_item.Quantity.Id
        col_name = self._col_name_delimiter.join([quantity_id, name])
        element_index = 0

        yield data_item.CreateTimeSeriesData(element_index), col_name

    def get_vector_values(self, data_set, data_item):
        name = Res1D.get_data_set_name(data_set)
        chainages = data_set.GetChainages(data_item)

        for i in range(data_item.NumberOfElements):
            quantity_id = data_item.Quantity.Id
            postfix = f"{chainages[i]:g}" if self._put_chainage_in_col_name else str(i)
            col_name_i = self._col_name_delimiter.join([quantity_id, name, postfix])

            yield data_item.CreateTimeSeriesData(i), col_name_i

    @staticmethod
    def get_data_set_name(data_set):
        name = data_set.Name if hasattr(data_set, "Name") else data_set.Id
        name = "" if name is None else name
        return name

    @property
    def time_index(self):
        """ pandas.DatetimeIndex of the time index. """
        if self._time_index is not None:
            return self._time_index

        time_stamps = [from_dotnet_datetime(t) for t in self.data.TimesList]
        self._time_index = pd.DatetimeIndex(time_stamps)
        return self._time_index

    @property
    def start_time(self):
        if self._start_time is not None:
            return self._start_time

        return from_dotnet_datetime(self.data.StartTime)

    @property
    def end_time(self):
        if self._end_time is not None:
            return self._end_time

        return from_dotnet_datetime(self.data.EndTime)

    @property
    def quantities(self):
        """ Quantities in res1d file. """
        return [quantity.Id for quantity in self._data.Quantities]

    @property
    def query(self):
        """
        .NET object ResultDataQuery to use for querying the loaded res1d data.

        More information about ResultDataQuery class see:
        https://manuals.mikepoweredbydhi.help/latest/General/Class_Library/DHI_MIKE1D/html/T_DHI_Mike1D_ResultDataAccess_ResultDataQuery.htm
        """
        return self._query

    @property
    def data(self):
        """
        .NET object ResultData with the loaded res1d data.

        More information about ResultData class see:
        https://manuals.mikepoweredbydhi.help/latest/General/Class_Library/DHI_MIKE1D/html/T_DHI_Mike1D_ResultDataAccess_ResultData.htm
        """
        return self._data

    @property
    def catchments(self):
        """ Catchments in res1d file. """
        return { Res1D.get_data_set_name(catchment): impl(catchment) for catchment in self._data.Catchments }

    @property
    def reaches(self):
        """ Reaches in res1d file. """
        return { Res1D.get_data_set_name(reach): impl(reach) for reach in self._data.Reaches }

    @property
    def nodes(self):
        """ Nodes in res1d file. """
        return { Res1D.get_data_set_name(node): impl(node) for node in self._data.Nodes }

    @property
    def global_data(self):
        """ Global data items in res1d file. """
        return { Res1D.get_data_set_name(gdat): impl(gdat) for gdat in self._data.GlobalData.DataItems }

    #region Query wrappers

    def get_catchment_values(self, catchment_id, quantity):
        return to_numpy(self.query.GetCatchmentValues(catchment_id, quantity))

    def get_node_values(self, node_id, quantity):
        return to_numpy(self.query.GetNodeValues(node_id, quantity))

    def get_reach_values(self, reach_name, chainage, quantity):
        return to_numpy(self.query.GetReachValues(reach_name, chainage, quantity))

    def get_reach_value(self, reach_name, chainage, quantity, time):
        time_dotnet = time if isinstance(time, DateTime) else to_dotnet_datetime(time)
        return self.query.GetReachValue(reach_name, chainage, quantity, time_dotnet)

    def get_reach_start_values(self, reach_name, quantity):
        return to_numpy(self.query.GetReachStartValues(reach_name, quantity))

    def get_reach_end_values(self, reach_name, quantity):
        return to_numpy(self.query.GetReachEndValues(reach_name, quantity))

    def get_reach_sum_values(self, reach_name, quantity):
        return to_numpy(self.query.GetReachSumValues(reach_name, quantity))

    #endregion Query wrapper
