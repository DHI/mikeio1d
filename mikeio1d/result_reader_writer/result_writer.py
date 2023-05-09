import numpy as np
import pandas as pd


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

    def modify(self, data_frame):
        """
        Modifies the ResultData object TimeData based on the provided data frame.
        It will override the relevant TimeData values by the values of the data frame.

        Parameters
        ----------
        data_frame : pandas.DataFrame
            Pandas data frame object with column names based on query labels
        """
        result_quantity_map = self.result_network.result_quantity_map

        for query_label in data_frame:
            result_quantity = result_quantity_map[query_label]
            element_index = result_quantity.element_index
            data_item = result_quantity.data_item

            values = data_frame[query_label]
            time_index = data_frame.index
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
            self.set_values_all(values.values, data_item, element_index)
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

        for time in time_index:
            value = float(values[time])
            i = res1d_time_index.get_loc(time)
            data_item.TimeData.SetValue(i, element_index, value)
