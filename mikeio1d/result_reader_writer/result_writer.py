import numpy as np
import pandas as pd

from ..quantities import TimeseriesId


class ResultWriter:
    """
    Class for modifying the ResultData object TimeData
    using the value of Pandas data frame.

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
        self.result_network = res1d.result_network

    def modify(self, dataframe: pd.DataFrame):
        """
        Modifies the ResultData object TimeData based on the provided data frame.
        It will override the relevant TimeData values by the values of the data frame.

        Parameters
        ----------
        dataframe : pandas.DataFrame
            Pandas dataframe object with TimeseriesId compatible multiindex.
        """
        for header, series in dataframe.items():
            timeseries_id = TimeseriesId.from_tuple(header)
            data_entry = timeseries_id.to_m1d(self.res1d)
            data_item = data_entry.data_item
            element_index = data_entry.element_index

            values = series.values
            time_index = series.index
            self.set_values(time_index, values, data_item, element_index)

    def set_values(self, time_index, values, data_item, element_index):
        """
        Modifies the TimeData value of the data item for given element index.

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
        """
        Sets the values of all entries in TimeData
        of the data item for given element index.
        """

        # Pick the first available value.
        # TODO: Some of the query IDs can be not unique. Figure out how to handle this case.
        values_count = len(values)
        is_float = not isinstance(values[0] if values_count > 0 else 0.0, np.ndarray)

        for i in range(values_count):
            value = float(values[i] if is_float else values[i][0])
            data_item.TimeData.SetValue(i, element_index, value)

    def set_values_indexed(self, time_index, values, data_item, element_index):
        """
        Sets only the provided for time_index and values in TimeData
        of the data item for given element index.
        """
        res1d_time_index = self.res1d.time_index

        # Pick just the first column.
        # TODO: Figure out how to handle multiple column case.
        if isinstance(values, pd.DataFrame):
            values = values.iloc[:, 0]

        length = len(values)
        if length != len(time_index):
            raise ValueError(
                f"Length of values ({length}) and time_index ({len(time_index)}) must be equal."
            )

        for i in range(length):
            time = time_index[i]
            value = float(values[i])
            timestep_index = res1d_time_index.get_loc(time)
            data_item.TimeData.SetValue(timestep_index, element_index, value)
