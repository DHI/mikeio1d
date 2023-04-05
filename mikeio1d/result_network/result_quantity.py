class ResultQuantity:
    """
    Class for wrapping a single ResultData data item quantity.

    ResultQuantity objects are the last attributes assigned to a network.
    They have the ability to add a query.

    Parameters
    ----------
    result_location: ResultLocation
        ResultLocation object, which could be node, catchment, grid point, or global data item.
    data_item: IDataItem
        MIKE 1D IDataItem object.
    res1d : Res1D
        Res1D object the quantity belongs to.
    """

    def __init__(self, result_location, data_item, res1d):
        self.result_location = result_location
        self.data_item = data_item
        self.res1d = res1d

    def add(self):
        """
        Add a query to ResultNetwork.queries based on the data item.
        """
        self.result_location.add_query(self.data_item)
