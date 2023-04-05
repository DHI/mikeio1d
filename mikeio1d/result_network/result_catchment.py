from ..query import QueryDataCatchment
from .result_location import ResultLocation


class ResultCatchment(ResultLocation):
    """
    Class for wrapping a single ResultData catchment.

    Parameters
    ----------
    catchment: IRes1DCatchment
        MIKE 1D IRes1DCatchment object.
    res1d : Res1D
        Res1D object the catchment belongs to.
    """

    def __init__(self, catchment, res1d):
        ResultLocation.__init__(self, catchment.DataItems, res1d)
        self.catchment = catchment
        self.set_quantities()

    def add_query(self, data_item):
        """ Add QueryDataCatchment to ResultNetwork.queries list."""
        quantity_id = data_item.Quantity.Id
        catchment_id = self.catchment.Id
        query = QueryDataCatchment(quantity_id, catchment_id)
        self.res1d.result_network.add_query(query)
