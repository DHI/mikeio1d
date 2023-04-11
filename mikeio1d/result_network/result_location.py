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

    Attributes
    ----------
    quantity_label : str
        A label, which is appended if the quantity id starts
        with a number. The value used is quantity_label = 'q_'
    result_quantity_map : dict
        Dictionary from quantity id to a list of ResultQuantity objects.
        For ResultLocation this list contains a single element.
    """

    def __init__(self, data_items, res1d):
        self.data_items = data_items
        self.res1d = res1d
        self.quantity_label = 'q_'
        self.result_quantity_map = {}

    def set_quantities(self):
        """ Sets all quantity attributes. """
        for data_item in self.data_items:
            self.set_quantity(self, data_item)

    def set_quantity(self, obj, data_item):
        """ Sets a single quantity attribute on the obj. """
        result_quantity = ResultQuantity(self, data_item, self.res1d)
        quantity = data_item.Quantity
        quantity_id = quantity.Id

        result_quantity_attribute_string = make_proper_variable_name(quantity_id, self.quantity_label)
        setattr(obj, result_quantity_attribute_string, result_quantity)

        self.add_to_result_quantity_maps(quantity_id, result_quantity)

    def add_to_result_quantity_maps(self, quantity_id, result_quantity):
        """
        Base method for adding to result quantity maps, which is a dictionary
        from quantity id to a list of result quantities corresponding to that
        quantity id.

        Parameters
        ----------
        quantity_id : str
            Quantity id.
        result_quantity : ResultQuantity
            One of the possible ResultQuantity objects corresponding to a quantity id.
        """
        pass

    def add_to_result_quantity_map(self, quantity_id, result_quantity, result_quantity_map):
        """
        Method for adding to a given result quantity map.

        Parameters
        ----------
        quantity_id : str
            Quantity id.
        result_quantity : ResultQuantity
            One of the possible ResultQuantity objects corresponding to a quantity id.
        result_quantity_map : dict
            Dictionary from quantity id to a list of ResultQuantity objects.
        """
        if quantity_id in result_quantity_map:
            result_quantity_map[quantity_id].append(result_quantity)
        else:
            result_quantity_map[quantity_id] = [result_quantity]

    def add_query(self, data_item):
        """ Base method for adding a query to ResultNetwork.queries list. """
        pass
