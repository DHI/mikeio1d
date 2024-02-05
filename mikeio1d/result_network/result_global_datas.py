from ..dotnet import pythonnet_implementation as impl
from .result_locations import ResultLocations
from .result_global_data import ResultGlobalData
from ..quantities import TimeSeriesIdGroup


class ResultGlobalDatas(ResultLocations):
    """
    Class for wrapping ResultData global data items.

    By itself it is also a dict, which contains
    mapping between global data item quantity ID
    and IDataItem object.

    Parameters
    ----------
    res1d : Res1D
        Res1D object the catchments belong to.

    Attributes
    ----------
    result_global_data_list : list of ResultGlobalData objects
        list of all ResultGlobalData objects corresponding to
        all res1d.data.GlobalData.DataItems.
    """

    def __init__(self, res1d):
        ResultLocations.__init__(self, res1d)
        self._group = TimeSeriesIdGroup.GLOBAL
        self.result_global_data_list = []
        self.set_global_data()

    def set_global_data(self):
        """
        Create the ResultGlobalData objects.
        No attributes are set here.
        """
        for data_item in self.data.GlobalData.DataItems:
            self.set_res1d_global_data_to_dict(data_item)
            result_global_data = ResultGlobalData(data_item, self, self.res1d)
            self.result_global_data_list.append(result_global_data)

    def set_res1d_global_data_to_dict(self, data_item):
        """
        Create a dict entry from data item quantity ID to IDatItem object.
        """
        data_item = impl(data_item)
        self[data_item.Quantity.Id] = data_item
