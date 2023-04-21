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
    element_indices : list
        List of integers representing element index for entries in data_items.
        For non grid point locations this is typically None.
    """

    def __init__(self, data_items, res1d):
        self.data_items = data_items
        self.res1d = res1d
        self.quantity_label = 'q_'
        self.result_quantity_map = {}
        self.element_indices = None

    def set_quantities(self):
        """ Sets all quantity attributes. """
        element_indices = self.element_indices
        data_items = list(self.data_items)
        data_items_count = len(data_items)
        for i in range(data_items_count):
            data_item = data_items[i]
            element_index = element_indices[i] if element_indices is not None else 0
            self.set_quantity(self, data_item, element_index)

    def set_quantity(self, obj, data_item, element_index=0):
        """ Sets a single quantity attribute on the obj. """
        result_quantity = ResultQuantity(self, data_item, self.res1d)
        result_quantity.element_index = element_index

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

    def add_to_network_result_quantity_map(self, query, result_quantity):
        """
        Method for adding to a network result quantity map, which is a dictionary
        from unique query label to a ResultQuantity object corresponding to that query.

        Parameters
        ----------
        query : QueryData
            One of the possible QueryData objects.
        result_quantity : ResultQuantity
            ResultQuantity object corresponding to a query label.
        """
        network_result_quantity_map = self.res1d.result_network.result_quantity_map
        network_result_quantity_map[str(query)] = result_quantity

    def add_query(self, data_item):
        """ Base method for adding a query to ResultNetwork.queries list. """
        query = self.get_query(data_item)
        self.res1d.result_network.add_query(query)

    def get_query(self, data_item):
        """ Base method for creating a query for given data item. """
        return None
