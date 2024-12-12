"""Res1D class."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from typing import List
    from typing import Optional
    from typing import Union
    from typing import Type
    from typing import Set

    from datetime import datetime

    import pandas as pd

    from .query import QueryData
    from .result_reader_writer.result_reader import ColumnMode

    from .result_network import ResultCatchments
    from .result_network import ResultNodes
    from .result_network import ResultReaches
    from .result_network import ResultStructures
    from .result_network import ResultGlobalDatas

    from DHI.Mike1D.ResultDataAccess import ResultData
    from DHI.Mike1D.ResultDataAccess import ResultDataSearcher
    from DHI.Mike1D.ResultDataAccess import ResultDataQuery

import os.path
import warnings

from pathlib import Path

from .dotnet import from_dotnet_datetime
from .dotnet import to_dotnet_datetime
from .dotnet import to_numpy

from .result_extractor import ExtractorCreator
from .result_extractor import ExtractorOutputFileType
from .result_network import ResultNetwork
from .result_network import ResultQuantity
from .result_reader_writer import ResultMerger
from .result_reader_writer import ResultReaderCreator
from .result_reader_writer import ResultReaderType
from .result_reader_writer import ResultWriter

from .query import QueryDataCatchment  # noqa: F401
from .query import QueryDataNode  # noqa: F401
from .query import QueryDataReach  # noqa: F401
from .query import QueryDataStructure  # noqa: F401
from .query import QueryDataGlobal  # noqa: F401

from .result_query.query_data_converter import QueryDataConverter

from .various import mike1d_quantities  # noqa: F401
from .various import NAME_DELIMITER
from .various import make_list_if_not_iterable

from .quantities import TimeSeriesId
from .quantities import get_default_derived_quantity_classes
from .quantities import DerivedQuantity

from .pandas_extension import Mikeio1dAccessor  # noqa: F401

from System import DateTime
from DHI.Mike1D.Generic import Connection


class Res1D:
    """Class for reading data from 1D network result files.

    Currently supported formats are:

    * MIKE 1D network and catchment res1d files
    * MIKE 1D Long Term Statistics (LTS) res1d files
    * EPANET res and resx files generated by MIKE+
    * SWMM out files
    * MOUSE legacy PRF and CRF files

    Parameters
    ----------
    file_path : str | Path
        File path of the result file.
    reaches : list[str] | None
        Reach IDs to include when pre-loading dynamic results. None includes all.
    nodes : list[str] | None
        Node IDs to include when pre-loading dynamic results. None includes all.
    catchments : list[str] | None
        Catchment IDs to include when pre-loading dynamic results. None includes all.
    time: slice | tuple[str] | list[str] | None
        Start and end time of the data to read. Using None will read all data.
    step_every : int | None
        Number specifying the time step frequency to output. None outputs all time steps.
    derived_quantities : list[str] | None
        Derived quantities to include when pre-loading dynamic results. None includes all.

    Examples
    --------
    Read all data from a res1d file into a Pandas DataFrame:
    >>> res = Res1D("results.res1d")
    >>> res.read()

    Read all available data for nodes:
    >>> res1d.nodes.read()

    Read data for a specific node:
    >>> res.nodes['node1'].read()

    Read data for a specific quantity:
    >>> res.nodes['node1'].WaterLevel.read()

    Filter which data is pre-loaded, typically used for large files:
    >>> nodes = ['node1', 'node2']
    >>> reaches = ['reach1', 'reach2']
    >>> times = slice('2020-01-01', '2020-01-02')
    >>> res1d = Res1D('MyRes1D.res1d', nodes=nodes, reaches=reaches, time=times)
    >>> res1d.read()

    Only read every second time step:
    >>> res1d = Res1D('MyRes1D.res1d', step_every=2)
    >>> res1d.read()
    """

    def __init__(
        self,
        file_path: Union[str, Path] = None,
        reaches: Optional[list[str]] = None,
        nodes: Optional[list[str]] = None,
        catchments: Optional[list[str]] = None,
        time: Union[tuple[str], list[str], slice, None] = None,
        step_every: Optional[int] = None,
        derived_quantities: Optional[list[str]] = None,
        **kwargs,
    ):
        # region deprecation

        self._issue_deprecation_warnings(kwargs)

        lazy_load = kwargs.get("lazy_load", False)
        col_name_delimiter = kwargs.get("col_name_delimiter", NAME_DELIMITER)
        put_chainage_in_col_name = kwargs.get("put_chainage_in_col_name", True)
        clear_queue_after_reading = kwargs.get("clear_queue_after_reading", True)
        header_load = kwargs.get("header_load", False)
        result_reader_type = kwargs.get("result_reader_type", ResultReaderType.COPIER)

        # endregion deprecation

        self.reader = ResultReaderCreator.create(
            result_reader_type,
            self,
            file_path,
            lazy_load,
            header_load,
            reaches,
            nodes,
            catchments,
            col_name_delimiter,
            put_chainage_in_col_name,
            time=time,
            step_every=step_every,
        )

        self.network = ResultNetwork(self)
        self.writer = ResultWriter(self)

        self.clear_queue_after_reading = clear_queue_after_reading

        self._derived_quantities = self._init_derived_quantities(derived_quantities)

    def __repr__(self):
        """Return string representation of the Res1D object."""
        return "<mikeio1d.Res1D>"

    def _issue_deprecation_warnings(self, kwargs):
        def warn_deprecation(name: str, hint: str = ""):
            if name in kwargs:
                warnings.warn(
                    f"The '{name}' parameter will be deprecated in 1.0. {hint}", FutureWarning
                )

        warn_deprecation("lazy_load")
        warn_deprecation("col_name_delimiter")
        warn_deprecation("put_chainage_in_col_name")
        warn_deprecation("clear_queue_after_reading")
        warn_deprecation(
            "header_load", "Dynamic data is read lazily, so header_load is not needed."
        )

    def _init_derived_quantities(
        self, derived_quantity_classes: List[Type[DerivedQuantity]] | None
    ) -> List[DerivedQuantity]:
        if derived_quantity_classes is None:
            derived_quantity_classes = get_default_derived_quantity_classes()

        for dq in derived_quantity_classes:
            self.add_derived_quantity(dq)

    def info(self) -> None:
        """Print information about the result file."""
        print(self._get_info())

    def _get_info(self) -> str:
        info = []
        if self.file_path:
            info.append(f"Start time: {str(self.start_time)}")
            info.append(f"End time: {str(self.end_time)}")
            info.append(f"# Timesteps: {str(self.reader.number_of_time_steps)}")
            info.append(f"# Catchments: {self.result_data.Catchments.get_Count()}")
            info.append(f"# Nodes: {self.result_data.Nodes.get_Count()}")
            info.append(f"# Reaches: {self.result_data.Reaches.get_Count()}")

            info.append(f"# Globals: {self.result_data.GlobalData.DataItems.Count}")
            for i, quantity in enumerate(self.result_data.Quantities):
                info.append(f"{i} - {ResultQuantity.prettify_quantity(quantity)}")

        info = str.join("\n", info)
        return info

    def read(
        self,
        queries: Optional[list[TimeSeriesId] | TimeSeriesId | list[QueryData] | QueryData] = None,
        column_mode: Optional[str | ColumnMode] = None,
    ) -> pd.DataFrame:
        """Read result data into a pandas DataFrame.

        Parameters
        ----------
        queries: list[TimeSeriesId] | TimeSeriesId | list[QueryData] | QueryData
            For internal use by mikeio1d. If None, reads all data.
        column_mode : str | ColumnMode (optional)
            Specifies the type of column index of returned DataFrame.
            'all' - column MultiIndex with levels matching TimeSeriesId objects.
            'compact' - same as 'all', but removes levels with default values.
            'timeseries' - column index of TimeSeriesId objects
            'str' - column index of str representations of QueryData objects

        Returns
        -------
        pd.DataFrame

        Notes
        -----
        The `queries` parameter is intended for internal use by mikeio1d. It mainly exists for historical
        reasons and is not recommended for general use. The preferred way to query data is via the fluent API,
        e.g. `res.nodes['node1'].WaterLevel.read()`.

        Examples
        --------
        >>> res = Res1D('results.res1d')
        >>> res1d.read()

        """
        timeseries_ids = self._get_timeseries_ids_to_read(queries)

        if len(timeseries_ids) == 0:
            return self.reader.read_all(column_mode=column_mode)

        df = self.reader.read(timeseries_ids, column_mode=column_mode)

        if self.clear_queue_after_reading:
            self.network.queue.clear()

        return df

    def _get_timeseries_ids_to_read(
        self, queries: List[QueryData] | List[TimeSeriesId]
    ) -> List[TimeSeriesId]:
        """Find out which list of TimeSeriesId objects should be used for reading."""
        queries = make_list_if_not_iterable(queries)

        if queries is None or len(queries) == 0:
            return self.network.queue

        is_already_time_series_ids = isinstance(queries[0], TimeSeriesId)
        if is_already_time_series_ids:
            return queries

        queries = QueryDataConverter.convert_queries_to_time_series_ids(self, queries)
        return queries

    def add_derived_quantity(self, derived_quantity: Type[DerivedQuantity]):
        """Add a derived quantity to the Res1D object, propogating changes to the network.

        Parameters
        ----------
        derived_quantity : Type[DerivedQuantity]
            Derived quantity to be added
        """
        derived_quantity = derived_quantity(self)
        self.network.add_derived_quantity(derived_quantity)

    def remove_derived_quantity(self, derived_quantity: Type[DerivedQuantity] | str):
        """Remove a derived quantity from the Res1D object, propogating changes to the network.

        Parameters
        ----------
        derived_quantity : DerivedQuantity | str
            Derived quantity to be removed. Either DerivedQuantity class or its name.

        """
        if isinstance(derived_quantity, type) and issubclass(derived_quantity, DerivedQuantity):
            derived_quantity = derived_quantity._NAME
        self.network.remove_derived_quantity(derived_quantity)

    def modify(self, data_frame: pd.DataFrame, file_path=None):
        """Modify the ResultData object TimeData based on the provided data frame.

        Parameters
        ----------
        data_frame : pandas.DataFrame
            Pandas data frame object with column names based on query labels
        file_path : str
            File path for the new res1d file. Optional.

        """
        self.reader.load_dynamic_data()
        self.writer.modify(data_frame)
        if file_path is not None:
            self.save(file_path)

    def save(self, file_path):
        """Save the ResultData to a new res1d file.

        Useful for persisting modified data, as well as converting supported result
        file types (e.g. res11) into res1d.

        Parameters
        ----------
        file_path : str
            File path for the new res1d file.

        Examples
        --------
        >>> res11_data = Res1D('results.res11')
        >>> res11_data.save('results.res1d')

        """
        self.reader.load_dynamic_data()
        connection_original = self.result_data.Connection
        self.result_data.Connection = Connection.Create(file_path)
        self.result_data.Save()
        self.result_data.Connection = connection_original

    def extract(
        self,
        file_path,
        queries: Optional[List[QueryData] | QueryData | List[TimeSeriesId] | TimeSeriesId] = None,
        time_step_skipping_number=1,
        ext=None,
    ):
        """Extract given queries to provided file.

        File type is determined from file_path extension.
        The supported formats are:
        * csv
        * dfs0
        * txt

        Parameters
        ----------
        file_path : str
            Output file path.
        queries : list
            List of queries.
        time_step_skipping_number : int
            Number specifying the time step frequency to output.
        ext : str
            Output file type to use instead of determining it from extension.
            Can be 'csv', 'dfs0', 'txt'.

        """
        self.reader.load_dynamic_data()

        ext = os.path.splitext(file_path)[-1] if ext is None else ext

        timeseries_ids = self._get_timeseries_ids_to_read(queries)
        data_entries = [t.to_data_entry(self) for t in timeseries_ids]

        extractor = ExtractorCreator.create(
            ext, file_path, data_entries, self.result_data, time_step_skipping_number
        )
        extractor.export()

        if self.clear_queue_after_reading:
            self.network.queue.clear()

    def to_csv(
        self,
        file_path,
        queries: Optional[List[QueryData] | QueryData | List[TimeSeriesId] | TimeSeriesId] = None,
        time_step_skipping_number=1,
    ):
        """Extract to csv file."""
        self.extract(file_path, queries, time_step_skipping_number, ExtractorOutputFileType.CSV)

    def to_dfs0(
        self,
        file_path,
        queries: Optional[List[QueryData] | QueryData | List[TimeSeriesId] | TimeSeriesId] = None,
        time_step_skipping_number=1,
    ):
        """Extract to dfs0 file."""
        self.extract(file_path, queries, time_step_skipping_number, ExtractorOutputFileType.DFS0)

    def to_txt(
        self,
        file_path,
        queries: Optional[List[QueryData] | QueryData | List[TimeSeriesId] | TimeSeriesId] = None,
        time_step_skipping_number=1,
    ):
        """Extract to txt file."""
        self.extract(file_path, queries, time_step_skipping_number, ExtractorOutputFileType.TXT)

    @staticmethod
    def merge(file_names: List[str] | List[Res1D], merged_file_name: str):
        """Merge res1d files.

        It is possible to merge three kinds of result files:
        * Regular res1d (HD, RR, etc.)
        * LTS extreme statistics
        * LTS chronological statistics

        For regular res1d files the requirement is that the simulation start time
        of the first file matches the simulation end time of the second file
        (the same principle for subsequent files).

        For LTS result files, meaningful merged result file is obtained when
        simulation periods for the files do not overlap.

        Parameters
        ----------
        file_names : list of str or Res1D objects
            List of res1d file names to merge.
        merged_file_name : str
            File name of the res1d file to store the merged data.

        """
        file_names = Res1D._convert_res1d_to_str_for_file_names(file_names)
        result_merger = ResultMerger(file_names)
        result_merger.merge(merged_file_name)

    @staticmethod
    def _convert_res1d_to_str_for_file_names(file_names: List[str] | List[Res1D]):
        file_names_new = []
        for i in range(len(file_names)):
            entry = file_names[i]
            file_name = entry.file_path if isinstance(entry, Res1D) else entry
            file_names_new.append(file_name)
        return file_names_new

    @staticmethod
    def get_supported_file_extensions() -> Set[str]:
        """Get supported file extensions for Res1D."""
        return {
            # MIKE 1D
            ".res1d",
            # MIKE 11
            ".res11",
            # MOUSE
            ".prf",
            ".crf",
            ".xrf",
            # EPANET
            ".res",
            # SWMM
            ".out",
            # Water Hammer
            ".whr",
            # EPANET, SWMM, Water Hammer
            ".resx",
        }

    @property
    def nodes(self) -> ResultNodes:
        """Nodes of the result file."""
        return self.network.nodes

    @property
    def reaches(self) -> ResultReaches:
        """Reaches of the result file."""
        return self.network.reaches

    @property
    def catchments(self) -> ResultCatchments:
        """Catchments of the result file."""
        return self.network.catchments

    @property
    def structures(self) -> ResultStructures:
        """Structures of the result file."""
        return self.network.structures

    @property
    def global_data(self) -> ResultGlobalDatas:
        """Global data of the result file."""
        return self.network.global_data

    @property
    def time_index(self) -> pd.DatetimeIndex:
        """pandas.DatetimeIndex of the time index."""
        return self.reader.time_index

    @property
    def start_time(self) -> datetime:
        """Start time of the result file."""
        return from_dotnet_datetime(self.result_data.StartTime)

    @property
    def end_time(self) -> datetime:
        """End time of the result file."""
        return from_dotnet_datetime(self.result_data.EndTime)

    @property
    def number_of_time_steps(self) -> int:
        """Number of time steps in the result file."""
        return self.reader.number_of_time_steps

    @property
    def quantities(self) -> List[str]:
        """Quantities in res1d file."""
        return self.reader.quantities

    @property
    def derived_quantities(self) -> List[str]:
        """Derived quantities available for res1d file."""
        dq = [
            *self.nodes.derived_quantities,
            *self.reaches.derived_quantities,
            *self.catchments.derived_quantities,
            *self.structures.derived_quantities,
        ]
        return list(set(dq))

    @property
    def file_path(self):
        """File path of the result file."""
        return self.reader.file_path

    @property
    def query(self) -> ResultDataQuery:
        """.NET object ResultDataQuery to use for querying the loaded res1d data.

        More information about ResultDataQuery class see:
        https://manuals.mikepoweredbydhi.help/latest/General/Class_Library/DHI_MIKE1D/html/T_DHI_Mike1D_ResultDataAccess_ResultDataQuery.htm
        """
        return self.reader.query

    @property
    def searcher(self) -> ResultDataSearcher:
        """.NET object ResultDataSearcher to use for searching res1d data items on network.

        More information about ResultDataSearcher class see:
        https://manuals.mikepoweredbydhi.help/latest/General/Class_Library/DHI_MIKE1D/html/T_DHI_Mike1D_ResultDataAccess_ResultDataQuery.htm
        """
        return self.reader.searcher

    @property
    def result_data(self) -> ResultData:
        """.NET object ResultData with the loaded res1d data.

        More information about ResultData class see:
        https://manuals.mikepoweredbydhi.help/latest/General/Class_Library/DHI_MIKE1D/html/T_DHI_Mike1D_ResultDataAccess_ResultData.htm
        """
        return self.reader.data

    @property
    def data(self) -> ResultData:
        """.NET object ResultData with the loaded res1d data.

        Alias for 'result_data' property.
        """
        return self.reader.data

    @property
    def result_type(self) -> str:
        """Specifies what type of result file Res1D is.

        Possible values:
        - Unknown
        - HD
        - RR
        - HDRR
        - LTSEvents
        - LTSAnnual
        - LTSMonthly
        """
        return self.result_data.ResultType.ToString()

    @property
    def projection_string(self) -> str:
        """Projection string of the result file."""
        return self.result_data.ProjectionString

    # region deprecation

    def read_all(self, column_mode: Optional[str | ColumnMode] = None) -> pd.DataFrame:
        """Read all data from res1d file to dataframe. Deprecated, use read() instead."""
        warnings.warn("This method will be deprecated in 1.0. Use read() instead.", FutureWarning)
        return self.read(column_mode=column_mode)

    def get_catchment_values(self, catchment_id, quantity):
        """Get catchment values. Deprecated, use network.catchments instead."""
        warnings.warn("This method will be deprecated in 1.0.", FutureWarning)
        self.reader.load_dynamic_data()
        return to_numpy(self.query.GetCatchmentValues(catchment_id, quantity))

    def get_node_values(self, node_id, quantity):
        """Get node values. Deprecated, use network.nodes instead."""
        warnings.warn("This method will be deprecated in 1.0.", FutureWarning)
        self.reader.load_dynamic_data()
        return to_numpy(self.query.GetNodeValues(node_id, quantity))

    def get_reach_values(self, reach_name, chainage, quantity):
        """Get reach values. Deprecated, use network.reaches instead."""
        warnings.warn("This method will be deprecated in 1.0.", FutureWarning)
        self.reader.load_dynamic_data()
        return to_numpy(self.query.GetReachValues(reach_name, chainage, quantity))

    def get_reach_value(self, reach_name, chainage, quantity, time):
        """Get reach value. Deprecated, use network.reaches instead."""
        warnings.warn("This method will be deprecated in 1.0.", FutureWarning)
        self.reader.load_dynamic_data()
        if self.reader.is_lts_result_file():
            raise NotImplementedError("The method is not implemented for LTS event statistics.")

        time_dotnet = time if isinstance(time, DateTime) else to_dotnet_datetime(time)
        return self.query.GetReachValue(reach_name, chainage, quantity, time_dotnet)

    def get_reach_start_values(self, reach_name, quantity):
        """Get reach start values. Deprecated, use network.reaches instead."""
        warnings.warn("This method will be deprecated in 1.0.", FutureWarning)
        self.reader.load_dynamic_data()
        return to_numpy(self.query.GetReachStartValues(reach_name, quantity))

    def get_reach_end_values(self, reach_name, quantity):
        """Get reach end values. Deprecated, use network.reaches instead."""
        warnings.warn("This method will be deprecated in 1.0.", FutureWarning)
        self.reader.load_dynamic_data()
        return to_numpy(self.query.GetReachEndValues(reach_name, quantity))

    def get_reach_sum_values(self, reach_name, quantity):
        """Get reach sum values. Deprecated, use network.reaches instead."""
        warnings.warn("This method will be deprecated in 1.0.", FutureWarning)
        self.reader.load_dynamic_data()
        return to_numpy(self.query.GetReachSumValues(reach_name, quantity))

    def clear_queue(self):
        """Clear the current active list of queries."""
        warnings.warn("This method will be deprecated in 1.0.", FutureWarning)
        self.network.queue.clear()

    @property
    def result_network(self) -> ResultNetwork:
        """Deprecated. Use network property instead."""
        warnings.warn(
            "The 'result_network' parameter will be deprecated in 1.0. Use 'network' instead.",
            FutureWarning,
        )
        return self.network

    # endregion deprecation


__all__ = [
    "Res1D",
    "ResultNodes",
    "ResultReaches",
    "ResultCatchments",
    "ResultStructures",
    "ResultGlobalDatas",
]
