"""ResultGlobalData class."""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from ..res1d import Res1D
    from .result_global_datas import ResultGlobalDatas
    from .result_quantity import ResultQuantity

    from DHI.Mike1D.ResultDataAccess import IDataItem
    from DHI.Mike1D.ResultDataAccess import IRes1DGlobalData

from ..query import QueryDataGlobal
from ..quantities import TimeSeriesIdGroup

from .result_location import ResultLocation
from .result_location import ResultLocationCreator


class ResultGlobalData(ResultLocation):
    """Class for wrapping ResultData global data items.

    By itself it is also a dict, which contains
    mapping between data item quantity ID and IDataItem object.

    Parameters
    ----------
    data_item : IDataItem
        MIKE 1D IDataItem object for a global data item.
    global_datas : ResultGlobalDatas object.
        A wrapper object for all global data items.
    res1d : Res1D
        Res1D object the global data belongs to.

    """

    def __init__(
        self,
        data_item: IDataItem,
        global_datas: ResultGlobalDatas,
        res1d: Res1D,
    ):
        ResultLocation.__init__(self)

        self._group = TimeSeriesIdGroup.GLOBAL

        self._creator = ResultGlobalDataCreator(self, data_item, global_datas, res1d)
        self._creator.create()

    def get_m1d_dataset(self, m1d_dataitem: IDataItem = None) -> IRes1DGlobalData:
        """Get IRes1DDataSet object associated with ResultGlobalData.

        Parameters
        ----------
        m1d_dataitem: IDataItem, optional
            Ignored for ResultGlobalData.

        Returns
        -------
        IRes1DDataSet
            IRes1DDataSet object associated with ResultGlobalData.

        """
        return self.res1d.result_data.GlobalData

    def get_query(self, data_item: IDataItem) -> QueryDataGlobal:
        """Get a QueryDataGlobal for given data item."""
        quantity_id = data_item.Quantity.Id
        query = QueryDataGlobal(quantity_id)
        return query


class ResultGlobalDataCreator(ResultLocationCreator):
    """Helper class for creating ResultGlobalData.

    Parameters
    ----------
    result_location:
        Instance of ResultCatchment, which the ResultCatchmentCreator deals with.
    data_item : IDataItem
        MIKE 1D IDataItem object for a global data item.
    global_datas : ResultGlobalDatas object.
        A wrapper object for all global data items.
    res1d : Res1D
        Res1D object the global data belongs to.

    """

    def __init__(
        self,
        result_location: ResultGlobalData,
        data_item: IDataItem,
        global_datas: ResultGlobalDatas,
        res1d: Res1D,
    ):
        ResultLocationCreator.__init__(self, result_location, [data_item], res1d)
        self.global_datas = global_datas
        self.data_item = data_item

    def create(self):
        """Perform ResultCatchment creation steps."""
        self.set_quantities()

    def set_quantities(self):
        """Set quantities for ResultGlobalData.

        Here only a single data item is used for ResultGlobalData.
        Also the quantity attribute is assigned to self.global_data.
        """
        self.set_quantity(self.global_datas, self.data_item)

    def add_to_result_quantity_maps(self, quantity_id: str, result_quantity: ResultQuantity):
        """Add global data result quantity to result quantity maps."""
        self.add_to_network_result_quantity_map(result_quantity)
