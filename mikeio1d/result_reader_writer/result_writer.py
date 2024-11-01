"""Module for ResultWriter class."""

import numpy as np
import pandas as pd

from ..quantities import TimeSeriesId


class ResultWriter:
    """Class for modifying the ResultData object TimeData using the value of Pandas data frame.

    Parameters
    ----------
    res1d : Res1D
        Res1D object the modified ResultData belongs to.

    Attributes
    ----------
    result_network : ResultNetwork
        ResultNetwork object corresponding to res1d.

    """

    def __init__(self, res1d):
        self.res1d = res1d
        self.result_network = res1d.network

    def modify(self, dataframe: pd.DataFrame):
        """Modify the ResultData object TimeData based on the provided data frame.

        It will override the relevant TimeData values by the values of the data frame.

        Parameters
        ----------
        dataframe : pandas.DataFrame
            Pandas dataframe object with TimeSeriesId compatible multiindex.

        """
        try:
            TimeSeriesId.try_from_obj(dataframe.columns[0])
        except ValueError:
            raise ValueError("The dataframe columns must be TimeSeriesId compatible multiindex.")

        for header, series in dataframe.items():
            timeseries_id = TimeSeriesId.try_from_obj(header)
            data_entry = timeseries_id.to_data_entry(self.res1d)
            data_item = data_entry.data_item
            element_index = data_entry.element_index

            values = series.to_numpy()
            time_index = series.index
            self.set_values(time_index, values, data_item, element_index)

    def set_values(self, time_index, values, data_item, element_index):
        """Modify the TimeData value of the data item for given element index.

        Parameters
        ----------
        time_index : pandas.DatetimeIndex
            Time stamps for the values.
        values : numpy.array
            NumPy array of values to write to TimeData.
        data_item : IDataItem
            MIKE 1D IDataItem object.
        element_index : int
            Element index into data item.

        """
        if len(values) == data_item.TimeData.NumberOfTimeSteps:
            self.set_values_all(values, data_item, element_index)
        else:
            self.set_values_indexed(time_index, values, data_item, element_index)

    def set_values_all(self, values, data_item, element_index):
        """Set the values of all entries in TimeData of the data item for given element index."""
        # Pick the first available value.
        # TODO: Some of the query IDs can be not unique. Figure out how to handle this case.
        values_count = len(values)
        is_float = not isinstance(values[0] if values_count > 0 else 0.0, np.ndarray)

        for i in range(values_count):
            value = float(values[i] if is_float else values[i][0])
            data_item.TimeData.SetValue(i, element_index, value)

    def set_values_indexed(self, time_index, values, data_item, element_index):
        """Set only the provided for time_index and values in TimeData of the data item for given element index."""
        res1d_time_index = self.res1d.time_index

        # Pick just the first column.
        # TODO: Figure out how to handle multiple column case.
        if isinstance(values, pd.DataFrame):
            values = values.iloc[:, 0]

        self._validate_time_index_values_pair(time_index, values)

        for i in range(len(values)):
            time = time_index[i]
            value = float(values[i])
            timestep_index = res1d_time_index.get_loc(time)
            data_item.TimeData.SetValue(timestep_index, element_index, value)

    def _validate_time_index_values_pair(self, time_index, values):
        if len(time_index) != len(values):
            raise ValueError(
                f"Length of time_index ({len(time_index)}) and values ({len(values)}) must be equal."
            )
