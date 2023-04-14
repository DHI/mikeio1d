from ..dotnet import pythonnet_implementation as impl
from .result_locations import ResultLocations
from .result_catchment import ResultCatchment
from .various import make_proper_variable_name


class ResultCatchments(ResultLocations):
    """
    Class for wrapping ResultData catchments.

    By itself it is also a dict, which contains
    mapping between catchment ID and IRes1DCatchment object.

    Parameters
    ----------
    res1d : Res1D
        Res1D object the catchments belong to.

    Attributes
    ----------
    catchment_label : str
        A label, which is appended if the catchment name starts
        with a number. The value used is catchment_label = 'c_'
    """

    def __init__(self, res1d):
        ResultLocations.__init__(self, res1d)
        self.catchment_label = 'c_'

        res1d.result_network.catchments = self
        self.set_catchments()
        self.set_quantity_collections()

    def set_catchments(self):
        """
        Set attributes to the current ResultCatchments object based
        on the catchment ID.
        """
        for catchment in self.data.Catchments:
            self.set_res1d_catchment_to_dict(catchment)
            result_catchment = ResultCatchment(catchment, self.res1d)
            result_catchment_attribute_string = make_proper_variable_name(catchment.Id, self.catchment_label)
            setattr(self, result_catchment_attribute_string, result_catchment)

    def set_res1d_catchment_to_dict(self, catchment):
        """
        Create a dict entry from catchment ID to IRes1DCatchment object.
        """
        catchment = impl(catchment)
        self[catchment.Id] = catchment
