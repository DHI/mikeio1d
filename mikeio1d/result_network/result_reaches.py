from ..dotnet import pythonnet_implementation as impl
from .result_locations import ResultLocations
from .result_reach import ResultReach
from .various import make_proper_variable_name


class ResultReaches(ResultLocations):
    """
    Class for wrapping ResultData reaches.

    By itself it is also a dict, which contains
    mapping between reach name and IRes1DReach object
    or a list of IRes1DReach objects.


    Parameters
    ----------
    res1d : Res1D
        Res1D object the reaches belong to.

    Attributes
    ----------
    reach_label : str
        A label, which is appended if the reach name starts
        with a number. The value used is reach_label = 'r_'
    result_reach_map : dict
        Dictionary from reach name to a list of ResultReach objects.
        This is needed, because the reach name is not necessarily unique and
        several reaches could have the same name.
    """

    def __init__(self, res1d):
        ResultLocations.__init__(self, res1d)
        self.reach_label = 'r_'
        self.result_reach_map = { }

        res1d.result_network.reaches = self
        self.set_reaches()
        self.set_quantity_collections()

    def set_reaches(self):
        """
        Set attributes to the current ResultReaches object based
        on the reach name.
        """
        for reach in self.data.Reaches:
            self.set_res1d_reach_to_dict(reach)
            result_reach = self.get_or_create_result_reach(reach)
            result_reach_attribute_string = make_proper_variable_name(reach.Name, self.reach_label)
            setattr(self, result_reach_attribute_string, result_reach)

    def set_quantity_collections(self):
        ResultLocations.set_quantity_collections(self)
        for reach_name in self.result_reach_map:
            result_reach = self.result_reach_map[reach_name]
            ResultLocations.set_quantity_collections(result_reach)

    def set_res1d_reach_to_dict(self, reach):
        """
        Create a dict entry from reach name to IRes1DReach object
        or a list of IRes1DReach objects.
        """
        self.set_res1d_object_to_dict(reach.Name, reach)

    def get_or_create_result_reach(self, reach):
        """
        Create or get already existing ResultReach object.
        There potentially could be just a single ResultReach object,
        for many IRes1DReach object, which have the same name.

        Also update a result_reach_map dict entry from reach name
        to a list of ResultReach objects.
        """
        result_reach_map = self.result_reach_map
        if reach.Name in result_reach_map:
            result_reach = result_reach_map[reach.Name]
            result_reach.add_res1d_reach(reach)
            return result_reach

        result_reach = ResultReach([reach], self.res1d)
        result_reach_map[reach.Name] = result_reach
        return result_reach
