from .result_location import ResultLocation
from .result_gridpoint import ResultGridPoint
from .various import make_proper_variable_name

from DHI.Mike1D.ResultDataAccess import Res1DGridPoint


class ResultReach(ResultLocation):
    """
    Class for wrapping a list of ResultData reaches
    having the same reach name.

    Parameters
    ----------
    reaches: list of IRes1DReach
        A list of MIKE 1D IRes1DReach objects having the same reach name.
    res1d : Res1D
        Res1D object the reach belongs to.

    Attributes
    ----------
    chainage_label : str
        A label, which is appended to all chainage attributes
        The value used is chainage_label = 'm_'
    data_items : list of IDataItems objects.
        A list of MIKE 1D IDataItems objects corresponding to a given reach name.
    result_gridpoints : list of lists of ResultGridPoint objects.
        A list containing lists of ResultGridPoint objects.
        Every list of ResultGridPoint objects correspond to a unique IRes1DReach.
    current_reach_result_gridpoints : list of ResultGridPoint objects.
        List of ResultGridPoint objects of currently processed IRes1DReach object.
        It is updated in set_gridpoints method.
    """

    def __init__(self, reaches, res1d):
        data_items = []
        ResultLocation.__init__(self, data_items, res1d)

        self.chainage_label = 'm_'

        self.result_gridpoints = []
        self.current_reach_result_gridpoints = None

        self.reaches = []
        for reach in reaches:
            self.add_res1d_reach(reach)

    def add_res1d_reach(self, reach):
        """
        Add a IRes1DReach to ResultReach.

        Parameters
        ----------
        reach: IRes1DReach
            A MIKE 1D IRes1DReach object.
        """
        self.reaches.append(reach)
        self.data_items.append(reach.DataItems)
        self.set_gridpoints(reach)
        self.set_gridpoint_data_items(reach)
        for result_gridpoint in self.current_reach_result_gridpoints:
            result_gridpoint.set_quantities()

    def set_gridpoints(self, reach):
        """
        Assign chainage attributes to a current ResultReach object
        from a data provided by IRes1DReach.

        Parameters
        ----------
        reach: IRes1DReach
            A MIKE 1D IRes1DReach object.
        """
        current_reach_result_gridpoints = []
        self.current_reach_result_gridpoints = current_reach_result_gridpoints
        self.result_gridpoints.append(current_reach_result_gridpoints)

        # For SWMM and EPANET results no grid points are defined
        # so introduce a single one.
        gridpoint_count = reach.GridPoints.Count
        if gridpoint_count == 0:
            gridpoint = Res1DGridPoint()
            self.set_gridpoint(reach, gridpoint)

        gridpoints = list(reach.GridPoints)
        for i in range(gridpoint_count):
            gridpoint = gridpoints[i]
            self.set_gridpoint(reach, gridpoint)

    def set_gridpoint(self, reach, gridpoint):
        """
        Assign chainage attribute to a current ResultReach object
        from a data provided by IRes1DReach and IRes1DGridPoint.

        Parameters
        ----------
        reach: IRes1DReach
            A MIKE 1D IRes1DReach object.
        gridpoint: IRes1DGridPoint
            A MIKE 1D IRes1DGridPoint object.
        """
        current_reach_result_gridpoints = self.current_reach_result_gridpoints

        result_gridpoint = ResultGridPoint(reach, gridpoint, reach.DataItems, self, self.res1d)
        current_reach_result_gridpoints.append(result_gridpoint)

        chainage_string = f'{gridpoint.Chainage:g}'
        result_gridpoint_attribute_string = make_proper_variable_name(chainage_string, self.chainage_label)
        setattr(self, result_gridpoint_attribute_string, result_gridpoint)

    def set_gridpoint_data_items(self, reach):
        """
        Assign data items to ResultGridPoint object belonging to current ResultReach
        from IRes1DReach data items.

        Parameters
        ----------
        reach: IRes1DReach
            A MIKE 1D IRes1DReach object.
        """
        for data_item in reach.DataItems:
            # For SWMM and EPANET results IndexList is None.
            index_list = [0] if data_item.IndexList is None else data_item.IndexList
            for gridpoint_index in index_list:
                result_gridpoint = self.current_reach_result_gridpoints[gridpoint_index]
                if data_item.ItemId is None:
                    result_gridpoint.add_data_item(data_item)
                else:
                    result_gridpoint.add_structure_data_item(data_item)
