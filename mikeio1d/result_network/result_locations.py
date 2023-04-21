from ..dotnet import pythonnet_implementation as impl
from .result_quantity_collection import ResultQuantityCollection
from .various import make_proper_variable_name


class ResultLocations(dict):
    """
    A base class for a network locations (nodes, reaches)
    or a catchments wrapper class.

    Parameters
    ----------
    res1d : Res1D
        Res1D object the result location belongs to.

    Attributes
    ----------
    data : ResultData
        MIKE 1D ResultData object.
    data_items : IDataItems.
        MIKE 1D IDataItems object.
    quantity_label : str
        A label, which is appended if the quantity id starts
        with a number. The value used is quantity_label = 'q_'
    result_quantity_map : dict
        Dictionary from quantity id to a list of ResultQuantity objects.
    """

    def __init__(self, res1d):
        self.res1d = res1d
        self.quantity_label = 'q_'
        self.data = res1d.data
        self.data_items = res1d.data.DataItems
        self.result_quantity_map = {}

    def set_quantity_collections(self):
        """ Sets all quantity collection attributes. """
        for quantity_id in self.result_quantity_map:
            result_quantities = self.result_quantity_map[quantity_id]
            result_quantity_collection = ResultQuantityCollection(result_quantities, self.res1d)
            result_quantity_attribute_string = make_proper_variable_name(quantity_id, self.quantity_label)
            setattr(self, result_quantity_attribute_string, result_quantity_collection)

    def set_res1d_object_to_dict(self, dict_key, obj):
        """
        Create a dict entry from a key name to an object
        or a list of objects.
        """
        obj = impl(obj)
        if dict_key in self:
            value = self[dict_key]
            if not isinstance(value, list):
                self[dict_key] = [value]

            self[dict_key].append(obj)
        else:
            self[dict_key] = obj
