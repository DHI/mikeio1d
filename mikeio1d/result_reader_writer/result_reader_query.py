import pandas as pd

from ..dotnet import pythonnet_implementation as impl
from .result_reader import ResultReader


class ResultReaderQuery(ResultReader):
    """
    Class for reading the ResultData object TimeData
    into Pandas data frame using ResultDataQuery object.
    """

    def read(self, queries=None):
        dfs = []
        for query in queries:
            df = pd.DataFrame(index=self.time_index)
            values = query.get_values(self.res1d)
            df[str(query)] = values
            dfs.append(df)

        df = pd.concat(dfs, axis=1)
        self.update_time_quantities(df)

        return df

    def read_all(self):
        dfs = []
        for data_set in self.data.DataSets:
            data_set = impl(data_set)
            if not self.is_data_set_included(data_set):
                continue

            for data_item in data_set.DataItems:
                values_name_pair = self.get_values(data_set, data_item)
                for values, col_name in values_name_pair:
                    df = pd.DataFrame(index=self.time_index)
                    df[col_name] = values
                    dfs.append(df)

        df = pd.concat(dfs, axis=1)
        self.update_time_quantities(df)
        return df

    def get_values(self, data_set, data_item):
        """ Get all time series values in given data_item. """
        for i in range(data_item.NumberOfElements):
            col_name = self.get_column_name(data_set, data_item, i)
            yield data_item.CreateTimeSeriesData(i), col_name
