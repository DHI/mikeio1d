"""Module for ResultReach class."""

from __future__ import annotations
import warnings
from typing import TYPE_CHECKING
from typing import Dict

if TYPE_CHECKING:  # pragma: no cover
    from typing import List

    from ..res1d import Res1D
    from ..geometry import ReachGeometry
    from .result_quantity import ResultQuantity

    from DHI.Mike1D.ResultDataAccess import IDataItem
    from DHI.Mike1D.ResultDataAccess import IRes1DReach
    from DHI.Mike1D.ResultDataAccess import IRes1DGridPoint

import numpy as np

from ..various import try_import_shapely
from ..quantities import TimeSeriesId
from ..quantities import TimeSeriesIdGroup
from ..dotnet import pythonnet_implementation as impl

from .result_location import ResultLocation
from .result_location import ResultLocationCreator
from .result_gridpoint import ResultGridPoint
from .various import make_proper_variable_name

from DHI.Mike1D.ResultDataAccess import Res1DGridPoint
from DHI.Mike1D.ResultDataAccess import Res1DCircularCrossSection
from DHI.Mike1D.ResultDataAccess import Res1DEggshapedCrossSection
from DHI.Mike1D.ResultDataAccess import Res1DRectangularCrossSection
from DHI.Mike1D.Generic import Quantity
from DHI.Mike1D.Generic import PredefinedQuantity


class ResultReach(ResultLocation, Dict[str, ResultGridPoint]):
    """Class for wrapping a list of ResultData reaches having the same reach name.

    Parameters
    ----------
    reaches: list of IRes1DReach
        A list of MIKE 1D IRes1DReach objects having the same reach name.
    res1d : Res1D
        Res1D object the reach belongs to.

    """

    def __init__(self, reaches: List[IRes1DReach], res1d: Res1D):
        ResultLocation.__init__(self)

        self._group = TimeSeriesIdGroup.REACH

        self._creator = ResultReachCreator(self, reaches, res1d)
        self._creator.create()

    def __repr__(self) -> str:
        """Return a string representation of ResultReach."""
        return f"<Reach: {self.name}>"

    def __getitem__(self, key: str | int) -> ResultGridPoint:
        """Get a ResultGridPoint object by chainage."""
        if isinstance(key, int):
            return self.gridpoints[key]
        return super().__getitem__(key)

    @property
    def res1d_reaches(self) -> List[IRes1DReach]:
        """List of DHI.Mike1D.ResultDataAccess.IRes1DReach corresponding to this result location."""
        return self._creator.reaches

    @property
    def chainages(self) -> List[str]:
        """List of chainages for the reach."""
        return list(self.keys())

    @property
    def gridpoints(self) -> List[ResultGridPoint]:
        """List of gridpoints for the reach."""
        return list(self.values())

    @property
    def geometry(self) -> ReachGeometry:
        """A geometric representation of the reach. Requires shapely."""
        try_import_shapely()
        from ..geometry import ReachGeometry

        return ReachGeometry.from_res1d_reaches(self.res1d_reaches)

    @property
    def name(self) -> str:
        """Name of the reach."""
        return self.res1d_reaches[0].Name

    @property
    def length(self) -> float | None:
        """Length of the reach."""
        return self._creator._get_total_length()

    @property
    def start_chainage(self) -> float:
        """Start chainage of the reach."""
        return self.res1d_reaches[0].LocationSpan.StartChainage

    @property
    def end_chainage(self) -> float:
        """End chainage of the reach."""
        return self.res1d_reaches[-1].LocationSpan.EndChainage

    @property
    def n_gridpoints(self) -> int:
        """Number of gridpoints in the reach."""
        return self._creator._get_total_gridpoints()

    @property
    def start_node(self) -> str | None:
        """Start node of the reach."""
        # For resx files, the start and end node indices are not available
        if self.res1d.file_path.endswith(".resx"):
            return None
        return self._creator._get_start_node()

    @property
    def end_node(self) -> str:
        """End node of the reach."""
        # For resx files, the start and end node indices are not available
        if self.res1d.file_path.endswith(".resx"):
            return None
        return self._creator._get_end_node()

    @property
    def height(self) -> float:
        """Height of the reach."""
        return self._creator._get_height()

    @property
    def full_flow_discharge(self) -> float:
        """Full flow discharge of the reach."""
        return self._creator._get_full_flow_discharge()

    def get_m1d_dataset(self, m1d_dataitem: IDataItem = None):
        """Get IRes1DDataSet object associated with ResultReach.

        A ResultReach may consist of several IRes1DDataSet objects. Therefore,
        a IRes1DDataItem must be provided to identify the correct IRes1DDataSet.

        Parameters
        ----------
        m1d_dataitem: IDataItem
            The IRes1DDataItem associated with the returned IRes1DDataSet.

        Returns
        -------
        IRes1DDataSet
            IRes1DDataSet object associated with ResultReach.

        """
        if m1d_dataitem is None:
            raise ValueError("m1d_dataitem must be provided for ResultReach.")

        for res1d_reach in self.res1d_reaches:
            if res1d_reach.DataItems.Contains(m1d_dataitem):
                return res1d_reach
        raise Exception(
            "No IRes1DDataSet found on reach for specified IRes1DDataItem: ",
            m1d_dataitem,
        )

    def get_query(self, data_item: IDataItem):
        """Get a query for a data item."""
        raise NotImplementedError("get_query not implemented for ResultReach. Use ResultGridPoint.")

    def interpolate_reach_ground_level(self, chainage: float) -> float:
        """Interpolate the ground level at a given chainage by linear interpolation from the bounding node ground levels.

        Parameters
        ----------
        chainage: float
            Chainage for which to interpolate the ground level.

        Returns
        -------
        float
            Interpolated ground level.

        """
        return self._creator._interpolate_reach_ground_level(chainage)

    def interpolate_reach_critical_level(self, chainage: float) -> float:
        """Interpolate the critical level at a given chainage by linear interpolation from the bounding node critical levels.

        Parameters
        ----------
        chainage: float
            Chainage for which to interpolate the critical level.

        Returns
        -------
        float
            Interpolated critical level.

        """
        return self._creator._interpolate_reach_critical_level(chainage)


class ResultReachCreator(ResultLocationCreator):
    """Helper class for creating ResultReach.

    Parameters
    ----------
    result_location : ResultReach
        Instance of ResultReach, which the ResultReachCreator deals with.
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

    def __init__(
        self,
        result_location: ResultReach,
        reaches: List[IRes1DReach],
        res1d: Res1D,
    ):
        data_items = []
        ResultLocationCreator.__init__(self, result_location, data_items, res1d)

        self.reaches_initial = reaches

        self.chainage_label = "m_"
        self.reaches: List[IRes1DReach] = []
        self.result_gridpoints: List[List[ResultGridPoint]] = []
        self.current_reach_result_gridpoints: List[ResultGridPoint] = None

    def create(self):
        """Perform ResultReach creation steps."""
        for reach in self.reaches_initial:
            self.add_res1d_reach(reach)

        self.set_static_attributes()

    def set_static_attributes(self):
        """Set static attributes. These show up in the html repr."""
        self.set_static_attribute("name")
        self.set_static_attribute("length")
        self.set_static_attribute("start_chainage")
        self.set_static_attribute("end_chainage")
        self.set_static_attribute("n_gridpoints")
        self.set_static_attribute("start_node")
        self.set_static_attribute("end_node")
        self.set_static_attribute("height")
        self.set_static_attribute("full_flow_discharge")

    def add_res1d_reach(self, reach: IRes1DReach):
        """Add a IRes1DReach to ResultReach.

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
            result_gridpoint._creator.set_quantities()

    def set_gridpoints(self, reach: IRes1DReach):
        """Assign chainage attributes to a current ResultReach object from a data provided by IRes1DReach.

        Parameters
        ----------
        reach: IRes1DReach
            A MIKE 1D IRes1DReach object.

        """
        current_reach_result_gridpoints: List[ResultGridPoint] = []
        self.current_reach_result_gridpoints = current_reach_result_gridpoints
        self.result_gridpoints.append(current_reach_result_gridpoints)

        # For SWMM and EPANET results no grid points are defined
        # so introduce a single one.
        gridpoint_count = reach.GridPoints.Count
        if gridpoint_count == 0:
            gridpoint = Res1DGridPoint()
            self.set_gridpoint(reach, gridpoint)

        gridpoints: List[IRes1DGridPoint] = list(reach.GridPoints)
        tag = self.create_reach_span_tag(gridpoints)
        for i in range(gridpoint_count):
            gridpoint = gridpoints[i]
            self.set_gridpoint(reach, gridpoint, tag)

    def create_reach_span_tag(self, gridpoints: List[IRes1DGridPoint]):
        """Create reach span tag to be set on ResultGridPoint."""
        if len(gridpoints) == 0:
            return ""

        start_gp = gridpoints[0]
        end_gp = gridpoints[-1]
        tag = TimeSeriesId.create_reach_span_tag_from_gridpoints(start_gp, end_gp)
        return tag

    def set_gridpoint(self, reach: IRes1DReach, gridpoint: IRes1DGridPoint, tag: str = ""):
        """Assign chainage attribute to a current ResultReach object from a data provided by IRes1DReach and IRes1DGridPoint.

        Parameters
        ----------
        reach: IRes1DReach
            A MIKE 1D IRes1DReach object.
        gridpoint: IRes1DGridPoint
            A MIKE 1D IRes1DGridPoint object.

        """
        current_reach_result_gridpoints = self.current_reach_result_gridpoints

        result_gridpoint = ResultGridPoint(
            reach, gridpoint, reach.DataItems, self.result_location, self.res1d, tag
        )
        current_reach_result_gridpoints.append(result_gridpoint)

        chainage_string = f"{gridpoint.Chainage:g}"
        result_gridpoint_attribute_string = make_proper_variable_name(
            chainage_string, self.chainage_label
        )
        setattr(self.result_location, result_gridpoint_attribute_string, result_gridpoint)

        chainage_str = f"{gridpoint.Chainage:.3f}"
        self.result_location[chainage_str] = result_gridpoint

    def set_gridpoint_data_items(self, reach: IRes1DReach):
        """Assign data items to ResultGridPoint object belonging to current ResultReach from IRes1DReach data items.

        Parameters
        ----------
        reach: IRes1DReach
            A MIKE 1D IRes1DReach object.

        """
        for data_item in reach.DataItems:
            # For SWMM and EPANET results IndexList is None.
            index_list = [0] if data_item.IndexList is None else list(data_item.IndexList)
            element_count = len(index_list)
            for element_index in range(element_count):
                gridpoint_index = index_list[element_index]
                result_gridpoint = self.current_reach_result_gridpoints[gridpoint_index]
                if data_item.ItemId is None:
                    result_gridpoint._creator.add_data_item(data_item, element_index)
                else:
                    result_gridpoint._creator.add_structure_data_item(data_item)

    def add_to_result_quantity_maps(self, quantity_id: str, result_quantity: ResultQuantity):
        """Add a quantity to the result quantity maps."""
        raise NotImplementedError(
            "add_to_result_quantity_maps not implemented for ResultReachCreatpr. Use ResultGridPointCreator."
        )

    def _get_total_length(self) -> float:
        total_length = 0
        for reach in self.reaches:
            if not hasattr(reach, "Length"):
                return None
            total_length += reach.Length
        return total_length

    def _get_total_gridpoints(self) -> int:
        return sum([len(gp_list) for gp_list in self.result_gridpoints])

    def _get_height(self) -> float:
        first_gridpoint = impl(self.result_location.gridpoints[0].gridpoint)

        if hasattr(first_gridpoint, "CrossSection"):
            cs = impl(first_gridpoint.CrossSection)
        else:
            cs = None

        if isinstance(cs, Res1DCircularCrossSection):
            return cs.Diameter
        elif isinstance(cs, Res1DEggshapedCrossSection):
            return cs.Diameter
        elif isinstance(cs, Res1DRectangularCrossSection):
            return cs.Height
        elif hasattr(cs, "Height"):
            return cs.Height
        else:
            return np.nan

    def _get_reach_for_chainage(self, chainage: float) -> IRes1DReach:
        """Return the relevant .NET Res1DReach for the specified chainage."""
        for reach in self.reaches:
            start_chainage = reach.LocationSpan.StartChainage
            end_chainage = reach.LocationSpan.EndChainage
            if chainage >= start_chainage and chainage <= end_chainage:
                return reach

        raise ValueError(f"Invalid chainage of {chainage} for reach {self.name}")

    def _get_start_node(self) -> str:
        """Return the start node of the reach."""
        return self.res1d.result_data.Nodes[self.reaches[0].StartNodeIndex].Id

    def _get_end_node(self) -> str:
        """Return the end node of the reach."""
        return self.res1d.result_data.Nodes[self.reaches[-1].EndNodeIndex].Id

    def _get_full_flow_discharge(self) -> float:
        """Return the full flow discharge of the reach."""
        ffd_quantity_type = Quantity.Create(PredefinedQuantity.FullReachDischarge)

        ffd_network_data = None
        for nd in self.res1d.result_data.NetworkDatas:
            if Quantity.ComparerDescription().Equals(nd.Quantity, ffd_quantity_type):
                ffd_network_data = nd
                break

        if ffd_network_data is None:
            return np.nan

        ffd_reach_data = ffd_network_data.GetReachData(self.reaches[0].Name)

        if ffd_reach_data is None:
            return np.nan

        return ffd_reach_data.GlobalValue

    def _interpolate_reach_ground_level(self, chainage: float) -> float:
        reach = self._get_reach_for_chainage(chainage)
        start_chainage = reach.LocationSpan.StartChainage
        end_chainage = reach.LocationSpan.EndChainage
        start_node = impl(self.res1d.result_data.Nodes[reach.StartNodeIndex])
        end_node = impl(self.res1d.result_data.Nodes[reach.EndNodeIndex])
        start_ground_level = start_node.GroundLevel
        end_ground_level = end_node.GroundLevel

        if start_ground_level is None or end_ground_level is None:
            return np.nan

        ground_slope = (end_ground_level - start_ground_level) / (end_chainage - start_chainage)
        return start_ground_level + ground_slope * (chainage - start_chainage)

    def _interpolate_reach_critical_level(self, chainage: float) -> float:
        reach = self._get_reach_for_chainage(chainage)
        start_chainage = reach.LocationSpan.StartChainage
        end_chainage = reach.LocationSpan.EndChainage
        start_node = impl(self.res1d.result_data.Nodes[reach.StartNodeIndex])
        end_node = impl(self.res1d.result_data.Nodes[reach.EndNodeIndex])
        start_critical_level = getattr(start_node, "CriticalLevel", None)
        end_critical_level = getattr(end_node, "CriticalLevel", None)

        if (
            start_critical_level is None
            or np.isnan(start_critical_level)
            or np.isinf(start_critical_level)
        ):
            start_critical_level = getattr(start_node, "GroundLevel", None)

        if (
            end_critical_level is None
            or np.isnan(end_critical_level)
            or np.isinf(end_critical_level)
        ):
            end_critical_level = getattr(end_node, "GroundLevel", None)

        if start_critical_level is None or end_critical_level is None:
            return np.nan

        critical_slope = (end_critical_level - start_critical_level) / (
            end_chainage - start_chainage
        )

        return start_critical_level + critical_slope * (chainage - start_chainage)
