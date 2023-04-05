from .result_quantity import ResultQuantity
from .various import make_proper_variable_name


class ResultLocation:
    """
    A base class for a network location (node, reach)
    or a catchment wrapper class.

    Parameters
    ----------
    data_items: IDataItems
        MIKE 1D IDataItems object.
    res1d : Res1D
        Res1D object the result location belongs to.
    """

    def __init__(self, data_items, res1d):
        self.data_items = data_items
        self.res1d = res1d

    def set_quantities(self):
        """ Sets all quantity attributes. """
        for data_item in self.data_items:
            self.set_quantity(self, data_item)

    def set_quantity(self, obj, data_item):
        """ Sets a single quantity attribute on the obj. """
        result_quantity = ResultQuantity(self, data_item, self.res1d)
        quantity = data_item.Quantity
        result_quantity_attribute_string = make_proper_variable_name(quantity.Id)
        setattr(obj, result_quantity_attribute_string, result_quantity)

    def add_query(self, data_item):
        """ Base method for adding a query to ResultNetwork.queries list. """
        pass
