"""ResultGlobalDatas class."""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from typing import List

    from ..res1d import Res1D

    from DHI.Mike1D.ResultDataAccess import IDataItem

from ..dotnet import pythonnet_implementation as impl
from ..quantities import TimeSeriesIdGroup

from .result_locations import ResultLocations
from .result_locations import ResultLocationsCreator
from .result_global_data import ResultGlobalData


class ResultGlobalDatas(ResultLocations):
    """Class for wrapping ResultData global data items.

    By itself it is also a dict, which contains
    mapping between global data item quantity ID
    and IDataItem object.

    Parameters
    ----------
    res1d : Res1D
        Res1D object the catchments belong to.

    """

    def __init__(self, res1d: Res1D):
        ResultLocations.__init__(self)
        self._group = TimeSeriesIdGroup.GLOBAL

        self._creator = ResultGlobalDatasCreator(self, res1d)
        self._creator.create()


class ResultGlobalDatasCreator(ResultLocationsCreator):
    """A helper class for creating ResultGlobalDatas.

    Parameters
    ----------
    result_locations : ResultGlobalDatas
        Instance of ResultGlobalDatas, which the ResultGlobalDatasCreator deals with.
    res1d : Res1D
        Res1D object the global data belong to.

    Attributes
    ----------
    result_global_data_list : list of ResultGlobalData objects
        list of all ResultGlobalData objects corresponding to
        all res1d.result_data.GlobalData.DataItems.

    """

    def __init__(self, result_locations: ResultGlobalDatas, res1d: Res1D):
        ResultLocationsCreator.__init__(self, result_locations, res1d)
        self.result_global_data_list: List[ResultGlobalData] = []

    def create(self):
        """Perform ResultCatchments creation steps."""
        self.set_global_data()

    def set_global_data(self):
        """Create the ResultGlobalData objects. No attributes are set here."""
        for data_item in self.data.GlobalData.DataItems:
            self.set_res1d_global_data_to_dict(data_item)
            result_global_data = ResultGlobalData(data_item, self.result_locations, self.res1d)
            self.result_global_data_list.append(result_global_data)

    def set_res1d_global_data_to_dict(self, data_item: IDataItem):
        """Create a dict entry from data item quantity ID to IDatItem object."""
        data_item = impl(data_item)
        self.result_locations[data_item.Quantity.Id] = data_item
