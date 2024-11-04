"""Module for ResultReaderQuery class."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from typing import Optional
    from typing import List
    from .result_reader import ResultReader
    from .result_reader import ColumnMode

    from ..query import QueryData


import pandas as pd

from ..dotnet import pythonnet_implementation as impl
from .result_reader import ResultReader
from ..quantities import TimeSeriesId
from ..result_query import QueryDataCreator


class ResultReaderQuery(ResultReader):
    """Class for reading the ResultData object TimeData into Pandas data frame using ResultDataQuery object."""

    def read(
        self, timeseries_ids: List[TimeSeriesId], column_mode: Optional[ColumnMode] = None
    ) -> pd.DataFrame:
        """Read the TimeData for given TimeSeriesIds into a Pandas data frame."""
        self.load_dynamic_data()

        if column_mode is not None:
            raise NotImplementedError(
                f"ResultReaderQuery does not support column_mode {column_mode}."
            )
        queries = [QueryDataCreator.from_timeseries_id(t) for t in timeseries_ids]

        dfs = []
        for query in queries:
            df = pd.DataFrame(index=self.time_index)
            values = query.get_values(self.res1d)
            df[str(query)] = values
            dfs.append(df)

        df = pd.concat(dfs, axis=1)
        df = df.astype("float32")
        self.update_time_quantities(df)

        return df

    def read_all(self, column_mode: Optional[ColumnMode] = None) -> pd.DataFrame:
        """Read all TimeData into a Pandas data frame."""
        self.load_dynamic_data()

        if column_mode is not None:
            raise NotImplementedError(
                f"ResultReaderQuery does not support column_mode {column_mode}."
            )

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
        df = df.astype("float32")
        self.update_time_quantities(df)
        return df

    def get_values(self, data_set, data_item):
        """Get all time series values in given data_item."""
        self.load_dynamic_data()

        for i in range(data_item.NumberOfElements):
            col_name = self.get_column_name(data_set, data_item, i)
            yield data_item.CreateTimeSeriesData(i), col_name
