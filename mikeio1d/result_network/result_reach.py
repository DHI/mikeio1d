from __future__ import annotations
import warnings
from typing import TYPE_CHECKING
from typing import Dict

if TYPE_CHECKING:  # pragma: no cover
    from ..geometry import ReachGeometry
    from typing import List

import numpy as np

from .result_location import ResultLocation
from .result_gridpoint import ResultGridPoint
from .various import make_proper_variable_name
from ..various import try_import_shapely
from ..quantities import TimeSeriesIdGroup
from ..dotnet import pythonnet_implementation as impl

from DHI.Mike1D.ResultDataAccess import Res1DGridPoint
from DHI.Mike1D.ResultDataAccess import Res1DCircularCrossSection
from DHI.Mike1D.ResultDataAccess import Res1DEggshapedCrossSection
from DHI.Mike1D.ResultDataAccess import Res1DRectangularCrossSection
from DHI.Mike1D.Generic import Quantity
from DHI.Mike1D.Generic import PredefinedQuantity


class ResultReach(ResultLocation, Dict[str, ResultGridPoint]):
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
        self._group = TimeSeriesIdGroup.REACH

        self.chainage_label = "m_"

        self.result_gridpoints = []
        self.current_reach_result_gridpoints = None

        self.reaches = []
        for reach in reaches:
            self.add_res1d_reach(reach)

        self.set_static_attributes()

    def __repr__(self) -> str:
        return f"<Reach: {self.name}>"

    def __getattr__(self, name: str):
        # TODO: Remove this in 1.0.0
        if hasattr(self.reaches[0], name):
            warnings.warn(
                f"Accessing IRes1DReach attribute {name} like this is deprecated. Use static attributes instead, or .reaches[0].{name}."
            )
            return getattr(self.reaches[0], name)
        else:
            object.__getattribute__(self, name)

    def __getitem__(self, key: str | int) -> ResultGridPoint:
        if isinstance(key, int):
            return self.gridpoints[key]
        return super().__getitem__(key)

    def _get_total_length(self):
        total_length = 0
        for reach in self.reaches:
            total_length += reach.Length
        return total_length

    def _get_total_gridpoints(self):
        return sum([len(gp_list) for gp_list in self.result_gridpoints])

    def _get_height(self) -> float:
        first_gridpoint = impl(self.gridpoints[0].gridpoint)

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

    def _get_reach_for_chainage(self, chainage: float):
        """
        Returns the relevant .NET Res1DReach for the specified chainage.
        """
        for reach in self.reaches:
            start_chainage = reach.LocationSpan.StartChainage
            end_chainage = reach.LocationSpan.EndChainage
            if chainage >= start_chainage and chainage <= end_chainage:
                return reach

        raise ValueError(f"Invalid chainage of {chainage} for reach {self.name}")

    def _get_start_node(self):
        """
        Returns the start node of the reach.
        """
        return self.res1d.data.Nodes[self.reaches[0].StartNodeIndex].Id

    def _get_end_node(self):
        """
        Returns the end node of the reach.
        """
        return self.res1d.data.Nodes[self.reaches[-1].EndNodeIndex].Id

    def _get_full_flow_discharge(self) -> float:
        """
        Returns the full flow discharge of the reach.
        """

        ffd_quantity_type = Quantity.Create(PredefinedQuantity.FullReachDischarge)

        ffd_network_data = None
        for nd in self.res1d.data.NetworkDatas:
            if Quantity.ComparerDescription().Equals(nd.Quantity, ffd_quantity_type):
                ffd_network_data = nd
                break

        if ffd_network_data is None:
            return np.nan

        ffd_reach_data = ffd_network_data.GetReachData(self.reaches[0].Name)

        if ffd_reach_data is None:
            return np.nan

        return ffd_reach_data.GlobalValue

    @property
    def chainages(self) -> List[str]:
        return list(self.keys())

    @property
    def gridpoints(self) -> List[ResultGridPoint]:
        return list(self.values())

    def set_static_attributes(self):
        """Set static attributes. These show up in the html repr."""
        self.set_static_attribute("name", self.reaches[0].Name)
        self.try_set_static_attribute_length()
        self.set_static_attribute(
            "start_chainage", self.reaches[0].LocationSpan.StartChainage
        )
        self.set_static_attribute(
            "end_chainage", self.reaches[-1].LocationSpan.EndChainage
        )
        self.set_static_attribute("n_gridpoints", self._get_total_gridpoints())
        # For resx files, the start and end node indices are not available
        if not self.res1d.file_path.endswith(".resx"):
            self.set_static_attribute("start_node", self._get_start_node())
            self.set_static_attribute("end_node", self._get_end_node())
        self.set_static_attribute("height", self._get_height())
        self.set_static_attribute(
            "full_flow_discharge", self._get_full_flow_discharge()
        )

    def try_set_static_attribute_length(self):
        try:
            self.set_static_attribute("length", self._get_total_length())
        except Exception as _:
            pass

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
        self.dataset = self.reaches

    def get_m1d_dataset(self, m1d_dataitem=None):
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
            IRes1DDataSet object associated with ResultReach."""

        if m1d_dataitem is None:
            raise ValueError("m1d_dataitem must be provided for ResultReach.")

        for m1d_reach in self.reaches:
            if m1d_reach.DataItems.Contains(m1d_dataitem):
                return m1d_reach
        raise Exception(
            "No IRes1DDataSet found on reach for specified IRes1DDataItem: ",
            m1d_dataitem,
        )

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

        result_gridpoint = ResultGridPoint(
            reach, gridpoint, reach.DataItems, self, self.res1d
        )
        current_reach_result_gridpoints.append(result_gridpoint)

        chainage_string = f"{gridpoint.Chainage:g}"
        result_gridpoint_attribute_string = make_proper_variable_name(
            chainage_string, self.chainage_label
        )
        setattr(self, result_gridpoint_attribute_string, result_gridpoint)

        chainage_str = f"{gridpoint.Chainage:.3f}"
        self[chainage_str] = result_gridpoint

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
            index_list = (
                [0] if data_item.IndexList is None else list(data_item.IndexList)
            )
            element_count = len(index_list)
            for element_index in range(element_count):
                gridpoint_index = index_list[element_index]
                result_gridpoint = self.current_reach_result_gridpoints[gridpoint_index]
                if data_item.ItemId is None:
                    result_gridpoint.add_data_item(data_item, element_index)
                else:
                    result_gridpoint.add_structure_data_item(data_item)

    def get_query(self, data_item):
        raise NotImplementedError(
            "get_query not implemented for ResultReach. Use ResultGridPoint."
        )

    def add_to_result_quantity_maps(self, quantity_id, result_quantity):
        raise NotImplementedError(
            "add_to_result_quantity_maps not implemented for ResultReach. Use ResultGridPoint."
        )

    @property
    def geometry(self) -> ReachGeometry:
        """
        A geometric representation of the reach. Requires shapely.
        """
        try_import_shapely()
        from ..geometry import ReachGeometry

        return ReachGeometry.from_m1d_reaches(self.reaches)

    def interpolate_reach_ground_level(self, chainage: float) -> float:
        """
        Interpolates the ground level at a given chainage by linear interpolation
        from the bounding node ground levels.

        Parameters
        ----------
        chainage: float
            Chainage for which to interpolate the ground level.

        Returns
        -------
        float
            Interpolated ground level.
        """
        reach = self._get_reach_for_chainage(chainage)
        start_chainage = reach.LocationSpan.StartChainage
        end_chainage = reach.LocationSpan.EndChainage
        start_node = impl(self.res1d.data.Nodes[reach.StartNodeIndex])
        end_node = impl(self.res1d.data.Nodes[reach.EndNodeIndex])
        start_ground_level = start_node.GroundLevel
        end_ground_level = end_node.GroundLevel

        if start_ground_level is None or end_ground_level is None:
            return np.nan

        ground_slope = (end_ground_level - start_ground_level) / (
            end_chainage - start_chainage
        )
        return start_ground_level + ground_slope * (chainage - start_chainage)

    def interpolate_reach_critical_level(self, chainage: float) -> float:
        """
        Interpolates the critical level at a given chainage by linear interpolation
        from the bounding node critical levels.

        Parameters
        ----------
        chainage: float
            Chainage for which to interpolate the critical level.

        Returns
        -------
        float
            Interpolated critical level.
        """
        reach = self._get_reach_for_chainage(chainage)
        start_chainage = reach.LocationSpan.StartChainage
        end_chainage = reach.LocationSpan.EndChainage
        start_node = impl(self.res1d.data.Nodes[reach.StartNodeIndex])
        end_node = impl(self.res1d.data.Nodes[reach.EndNodeIndex])
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
