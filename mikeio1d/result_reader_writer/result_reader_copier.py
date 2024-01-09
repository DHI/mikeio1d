from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import List
    from ..result_query import QueryData

import numpy as np
import pandas as pd

from ..dotnet import pythonnet_implementation as impl
from ..various import NAME_DELIMITER
from .result_reader import ResultReader
from ..quantities import TimeseriesId

from System import IntPtr

from DHI.Mike1D.MikeIO import ResultDataCopier
from DHI.Mike1D.MikeIO import DataEntry as DataEntryNet


class ResultReaderCopier(ResultReader):
    """
    Class for reading the ResultData object TimeData
    into Pandas data frame using ResultDataCopier object
    from DHI.Mike1D.MikeIO library.
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
        ResultReader.__init__(
            self,
            res1d,
            file_path,
            lazy_load,
            header_load,
            reaches,
            nodes,
            catchments,
            col_name_delimiter,
            put_chainage_in_col_name,
        )

        self.result_data_copier = ResultDataCopier(self.data)

    def read(self, queries: List[QueryData] = None):
        timerseries_ids: List[TimeseriesId] = []
        data_entries = self.result_data_copier.GetEmptyDataEntriesList()
        for query in queries:
            query.add_to_data_entries(self.res1d, data_entries, timerseries_ids)

        df = self.create_data_frame(data_entries, timerseries_ids)
        return df

    def read_all(self):
        data_entries, timeseries_ids = self.get_all_data_entries_and_timeseries_ids()
        df = self.create_data_frame(data_entries, timeseries_ids)
        return df

    def create_data_frame(self, data_entries, timeseries_ids: List[TimeseriesId]):
        number_of_timesteps = self.data.NumberOfTimeSteps
        number_of_items = len(data_entries)

        shape = (number_of_timesteps, number_of_items)
        data_array = np.zeros(shape, dtype=np.dtype("float32"), order="F")

        data_pointer = data_array.ctypes.data
        data_pointer_net = IntPtr(data_pointer)
        self.result_data_copier.CopyData(data_pointer_net, data_entries)

        columns = TimeseriesId.to_multiindex(timeseries_ids)

        df = pd.DataFrame(data_array, index=self.time_index, columns=columns)

        self.update_time_quantities(df)

        return df

    def get_all_data_entries_and_timeseries_ids(self):
        data_entries = self.result_data_copier.GetEmptyDataEntriesList()
        timeseries_ids: List[TimeseriesId] = []
        for data_set in self.data.DataSets:
            data_set = impl(data_set)
            if not self.is_data_set_included(data_set):
                continue

            for data_item in data_set.DataItems:
                for i in range(data_item.NumberOfElements):
                    data_entry = DataEntryNet(data_item, i)
                    data_entries.Add(data_entry)

                    timeseries_id = TimeseriesId.from_dataset_dataitem_and_element(
                        data_set, data_item, i
                    )
                    timeseries_ids.append(timeseries_id)

        return data_entries, timeseries_ids
