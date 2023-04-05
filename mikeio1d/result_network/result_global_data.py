from .result_location import ResultLocation


class ResultGlobalData(ResultLocation):
    """
    Class for wrapping ResultData global data items.

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

    def __init__(self, data_item, global_datas, res1d):
        ResultLocation.__init__(self, [data_item], res1d)
        self.data_item = data_item
        self.global_datas = global_datas
        self.set_quantities()

    def set_quantities(self):
        """
        Override of base set_quantities.
        Here only a single data item is used for ResultGlobalData.
        Also the quantity attribute is assigned to self.global_data.
        """
        data_item = self.data_item
        self.set_quantity(self.global_datas, data_item)

    def add_query(self, data_item):
        """
        TODO: Needs an implementation when QueryDataGlobal is available.
        """
        pass
