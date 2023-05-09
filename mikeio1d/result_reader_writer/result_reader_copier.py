import numpy as np
import pandas as pd

from ..dotnet import pythonnet_implementation as impl
from ..various import NAME_DELIMITER
from .result_reader import ResultReader

from System import IntPtr

from DHI.Mike1D.MikeIO import ResultDataCopier
from DHI.Mike1D.MikeIO import DataEntry as DataEntryNet


class ResultReaderCopier(ResultReader):
    """
    Class for reading the ResultData object TimeData
    into Pandas data frame using ResultDataCopier object
    from DHI.Mike1D.MikeIO library.
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

        ResultReader.__init__(
            self, res1d, file_path, lazy_load, header_load,
            reaches, nodes, catchments,
            col_name_delimiter, put_chainage_in_col_name)

        self.result_data_copier = ResultDataCopier(self.data)

    def read(self, queries=None):
        column_names = []
        data_entries = self.result_data_copier.GetEmptyDataEntriesList()
        for query in queries:
            query.add_to_data_entries(self.res1d, data_entries, column_names)

        df = self.create_data_frame(data_entries, column_names)
        return df

    def read_all(self):
        data_entries, column_names = self.get_all_data_entries_and_column_names()
        df = self.create_data_frame(data_entries, column_names)
        return df

    def create_data_frame(self, data_entries, column_names):
        number_of_timesteps = self.data.NumberOfTimeSteps
        number_of_items = len(data_entries)

        shape = (number_of_timesteps, number_of_items)
        data_array = np.zeros(shape, dtype=np.dtype('float32'), order='F')

        data_pointer = data_array.ctypes.data
        data_pointer_net = IntPtr(data_pointer)
        self.result_data_copier.CopyData(data_pointer_net, data_entries)

        df = pd.DataFrame(data_array, index=self.time_index, columns=column_names)

        self.update_time_quantities(df)

        return df

    def get_all_data_entries_and_column_names(self):
        data_entries = self.result_data_copier.GetEmptyDataEntriesList()
        column_names = []
        for data_set in self.data.DataSets:
            data_set = impl(data_set)
            if not self.is_data_set_included(data_set):
                continue

            for data_item in data_set.DataItems:
                for i in range(data_item.NumberOfElements):
                    data_entry = DataEntryNet(data_item, i)
                    data_entries.Add(data_entry)

                    column_name = self.get_column_name(data_set, data_item, i)
                    column_names.append(column_name)

        return data_entries, column_names
