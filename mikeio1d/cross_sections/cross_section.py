"""CrossSection class."""

from __future__ import annotations
from warnings import warn

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Iterable
    from typing import Tuple
    from typing import List
    from ..geometry import CrossSectionGeometry

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from .cross_section_factory import CrossSectionFactory
from .marker import Marker
from .enums import RadiusType
from .enums import ResistanceType
from .enums import ResistanceDistribution
from .enums import ProcessLevelsMethod

from ..various import try_import_shapely

import System
from DHI.Mike1D.CrossSectionModule import CrossSectionPoint
from DHI.Mike1D.CrossSectionModule import ICrossSection
from DHI.Mike1D.Generic import ProcessingOption
from DHI.Mike1D.Generic import ResistanceDistribution as m1d_ResistanceDistribution
from DHI.Mike1D.Generic import ResistanceFormulation as m1d_ResistanceFormulation
from DHI.Mike1D.Generic import RadiusType as m1d_RadiusType
from DHI.Mike1D.Generic import ZLocation
from DHI.Mike1D.Generic.Spatial.Geometry import Coordinate
from DHI.Mike1D.Generic.Spatial.Geometry import CoordinateList


class CrossSection:
    """A cross section in MIKE 1D, uniquely identified by a location ID, chainage, and topo ID.

    Parameters
    ----------
    m1d_cross_section: ICrossSection
        The MIKE 1D cross section object.

    Notes
    -----
    Support is currently limited to open cross sections with raw data.

    Examples
    --------
    >>> from mikeio1d.cross_sections import CrossSection
    >>> x = [0, 10, 20, 30, 40, 50]
    >>> z = [0, 2, 3, 4, 3, 0]
    >>> cs = CrossSection.from_xz(x, z, location_id="loc1", chainage=100, topo_id="topo1")
    """

    def __init__(self, m1d_cross_section: ICrossSection):
        if hasattr(m1d_cross_section, "__implementation__"):
            m1d_cross_section = m1d_cross_section.__implementation__

        self._m1d_cross_section = m1d_cross_section

    @staticmethod
    def from_xz(
        x: Iterable[float],
        z: Iterable[float],
        location_id: str,
        chainage: float,
        topo_id: str,
        default_markers: bool = True,
    ) -> CrossSection:
        """Create an open cross section from xz data.

        Parameters
        ----------
        x : Iterable[float]
            The x coordinates of the cross section.
        z : Iterable[float]
            The z coordinates of the cross section.
        location_id : str
            Location ID of the cross section.
        chainage : float
            Chainage of the cross section.
        topo_id : str
            Topo ID of the cross section.
        default_markers : bool, optional
            If True, default markers will be added to the cross section.

        Returns
        -------
        cross_section : CrossSection

        """
        m1d_cross_section = CrossSectionFactory.create_open_from_xz_data(
            x, z, location_id, chainage, topo_id, default_markers
        )
        return CrossSection(m1d_cross_section)

    def __repr__(self) -> str:
        """Return a string representation of the cross section."""
        return f"<CrossSection: {self.location_id}, {format(self.chainage, '.3f')}, {self.topo_id}>"

    @property
    def m1d_cross_section(self) -> ICrossSection:
        """The DHI.Mike1D.CrossSectionModule.ICrossSection object that CrossSection wraps."""
        return self._m1d_cross_section

    @property
    def topo_id(self) -> str:
        """Topo ID of the cross section."""
        return self._m1d_cross_section.TopoID

    @property
    def location_id(self) -> str:
        """Location ID of the cross section."""
        return self._m1d_cross_section.Location.ID

    @property
    def chainage(self) -> float:
        """Chainage of the cross section."""
        return self._m1d_cross_section.Location.Chainage

    @property
    def location(self) -> ZLocation:
        """Location of the cross section (DHI.Mike1D.Generic.ZLocation object)."""
        return self._m1d_cross_section.Location

    @property
    def bottom_level(self) -> float:
        """Bottom level of the cross section."""
        return self._m1d_cross_section.BottomLevel

    @property
    def height(self) -> float:
        """Height of the cross section."""
        return self._m1d_cross_section.Height

    @property
    def interpolated(self) -> bool:
        """Is the cross section interpolated? (i.e. not measured)."""
        return self._m1d_cross_section.Interpolated

    @property
    def is_open(self) -> bool:
        """Is the cross section open? (i.e. not closed)."""
        return self._m1d_cross_section.IsOpen

    @property
    def max_width(self) -> float:
        """Maximum width of the cross section."""
        return self._m1d_cross_section.MaximumWidth

    @property
    def min_water_depth(self) -> float:
        """Minimum water depth of the cross section.

        If the water depth goes below this depth, it will be corrected to match this depth.

        This can be negative, in case the cross section has a slot attached.
        """
        return self._m1d_cross_section.MinWaterDepth

    @property
    def zmax(self) -> float:
        """Maximum elevation of the cross section."""
        return self._m1d_cross_section.ZMax

    @property
    def zmin(self) -> float:
        """Minimum elevation of the cross section."""
        return self._m1d_cross_section.ZMin

    @property
    def geometry(self) -> CrossSectionGeometry:
        """The geographical geometry of the cross section line."""
        try_import_shapely()
        from ..geometry import CrossSectionGeometry

        return CrossSectionGeometry(self._m1d_cross_section)

    @property
    def coords(self) -> Tuple[Tuple[float, float]]:
        """Get the geographical coordinates of the cross section line.

        If the cross section has no coordinates, an empty tuple will be returned.

        Returns
        -------
        coords : Tuple[Tuple[float, float]]
            A tuple of (x, y) coordinates.

        """
        if self._m1d_cross_section.Coordinates is None:
            return tuple()
        return tuple((p.X, p.Y) for p in self._m1d_cross_section.Coordinates)

    @coords.setter
    def coords(self, coords: List[Tuple[float, float]]):
        """Set the geographical coordinates of the cross section line.

        Parameters
        ----------
        coords : List[Tuple[float, float]]
            A list of (x, y) coordinates.

        """
        coord_list = CoordinateList()
        for x, y in coords:
            coord_list.Add(Coordinate.CreateXY(x, y))
        self._m1d_cross_section.Coordinates = coord_list

    @property
    def resistance_type(self) -> ResistanceType:
        """int, ResistanceType: The type of resistance used by the cross section.

        0 - Relative
        1 - Manning's n
        2 - Manning's M
        3 - Chezy number
        4 - Darcy-Weisbach
        5 - Colebrook White
        6 - Hazen Williams
        """
        return ResistanceType(
            int(self._m1d_cross_section.BaseCrossSection.FlowResistance.Formulation)
        )

    @resistance_type.setter
    def resistance_type(self, value: int | ResistanceType):
        self._m1d_cross_section.BaseCrossSection.FlowResistance.Formulation = (
            m1d_ResistanceFormulation(value)
        )

    @property
    def resistance_distribution(self) -> ResistanceDistribution:
        """int, ResistanceDistribution: The distribution of resistance used in the cross section.

        0 - Uniform
        1 - Zones
        2 - Distributed
        3 - Constant
        4 - ExponentVarying
        """
        return ResistanceDistribution(
            int(self._m1d_cross_section.BaseCrossSection.FlowResistance.ResistanceDistribution)
        )

    @resistance_distribution.setter
    def resistance_distribution(self, value: int | ResistanceDistribution):
        self._m1d_cross_section.BaseCrossSection.FlowResistance.ResistanceDistribution = (
            m1d_ResistanceDistribution(value)
        )

    def _warn_if_resistance_distribution_is_not_zones(self):
        if self.resistance_distribution != ResistanceDistribution.ZONES:
            message = (
                "You are accessing/setting zone resistances without the correct resistance distribution type. "
                "Set the resistance distribution type to zones by setting '.resistance_distribution' to 1."
            )
            warn(message)

    @property
    def resistance_left_high_flow(self) -> float:
        """float: Resistance for the left high flow zone.

        Notes
        -----
        This property is only relevant if the resistance distribution is set to zones.
        """
        self._warn_if_resistance_distribution_is_not_zones()
        return self._m1d_cross_section.BaseCrossSection.FlowResistance.ResistanceLeftHighFlow

    @resistance_left_high_flow.setter
    def resistance_left_high_flow(self, value: float):
        self._warn_if_resistance_distribution_is_not_zones()
        self._m1d_cross_section.BaseCrossSection.FlowResistance.ResistanceLeftHighFlow = value

    @property
    def resistance_low_flow(self) -> float:
        """float: Resistance for the low flow zone.

        Notes
        -----
        This property is only relevant if the resistance distribution is set to zones.
        """
        self._warn_if_resistance_distribution_is_not_zones()
        return self._m1d_cross_section.BaseCrossSection.FlowResistance.ResistanceLowFlow

    @resistance_low_flow.setter
    def resistance_low_flow(self, value: float):
        self._warn_if_resistance_distribution_is_not_zones()
        self._m1d_cross_section.BaseCrossSection.FlowResistance.ResistanceLowFlow = value

    @property
    def resistance_right_high_flow(self) -> float:
        """float: Resistance for the right high flow zone.

        Notes
        -----
        This property is only relevant if the resistance distribution is set to zones.
        """
        self._warn_if_resistance_distribution_is_not_zones()
        return self._m1d_cross_section.BaseCrossSection.FlowResistance.ResistanceRightHighFlow

    @resistance_right_high_flow.setter
    def resistance_right_high_flow(self, value: float):
        self._warn_if_resistance_distribution_is_not_zones()
        self._m1d_cross_section.BaseCrossSection.FlowResistance.ResistanceRightHighFlow = value

    @property
    def radius_type(self) -> RadiusType:
        """int, RadiusType: The type of hydraulic radius used in the cross section.

        0 - Resistance radius
        1 - Hydraulic radius, effective area
        2 - Hydraulic radius, total area
        """
        return RadiusType(int(self._m1d_cross_section.BaseCrossSection.RadiusType))

    @radius_type.setter
    def radius_type(self, radius_type: int | RadiusType):
        self._m1d_cross_section.BaseCrossSection.RadiusType = m1d_RadiusType(int(radius_type))

    @property
    def number_of_processing_levels(self) -> int:
        """int: The number of levels used in the processed data.

        Notes
        -----
        Setting this will both recalculate processed data and change the processing_levels_method to automatic.

        """
        pls = self._m1d_cross_section.BaseCrossSection.ProcessingLevelsSpecs
        if pls.Option == ProcessingOption.EquidistantLevels:
            return pls.NoOfLevels
        else:
            return len(self.processing_levels)

    @number_of_processing_levels.setter
    def number_of_processing_levels(self, value: int):
        pls = self._m1d_cross_section.BaseCrossSection.ProcessingLevelsSpecs
        pls.Option = ProcessingOption.AutomaticLevels
        pls.NoOfLevels = value
        self._m1d_cross_section.BaseCrossSection.CalculateProcessedData()

    @property
    def processing_levels(self) -> Tuple[float]:
        """tuple[float]: A tuple of the level elevations used in the processed data.

        Notes
        -----
        Setting this will recalculate the processed data using only the specified levels.
        The minimum and maximum levels will be automatically added if not already present.
        """
        return tuple(self._m1d_cross_section.BaseCrossSection.ProcessedLevels)

    @processing_levels.setter
    def processing_levels(self, levels: Iterable[float]):
        pls = self._m1d_cross_section.BaseCrossSection.ProcessingLevelsSpecs
        pls.Option = ProcessingOption.UserDefinedLevels
        pls.UserDefLevels = tuple(levels)
        self._m1d_cross_section.BaseCrossSection.CalculateProcessedData()

    @property
    def processing_levels_method(self) -> ProcessLevelsMethod:
        """int, ProcessLevelMethod: The method used to generate processing levels.

        0 - Automatic
        1 - Equidistant
        2 - User defined
        """
        return ProcessLevelsMethod(
            int(self._m1d_cross_section.BaseCrossSection.ProcessingLevelsSpecs.Option)
        )

    @processing_levels_method.setter
    def processing_levels_method(self, processing_level_method: int | ProcessLevelsMethod):
        self._m1d_cross_section.BaseCrossSection.ProcessingLevelsSpecs.Option = ProcessingOption(
            int(processing_level_method)
        )
        self._m1d_cross_section.BaseCrossSection.CalculateProcessedData()

    @property
    def processed_allow_recompute(self) -> bool:
        """bool: Whether the processed data can be recomputed (e.g. if the raw data has changed).

        Setting this to False will freeze the processed data values in their current state.

        Default is True.
        """
        return not self._m1d_cross_section.BaseCrossSection.ProcessedDataProtected

    @processed_allow_recompute.setter
    def processed_allow_recompute(self, value: bool):
        self._m1d_cross_section.BaseCrossSection.ProcessedDataProtected = not value

    def recompute_processed(self):
        """Recompute the processed data.

        Notes
        -----
        In most cases this is not necessary as it will be done automatically when the raw data changes.
        If processed_allow_recompute is set to False, then this will do nothing.
        """
        self._m1d_cross_section.BaseCrossSection.CalculateProcessedData()

    def _calculate_conveyance_factor(
        self, resistance: Tuple[float], flow_area: Tuple[float], radius: Tuple[float]
    ) -> Tuple[float]:
        """Calculate the conveyance factor from resistance, flow area and radius.

        Note that this is not the true conveyance factor since resistance could be relative. However,
        this is the same calculation provided by MIKE+ cross section editor. Its main purpose is for checking
        that conveyance values will be monotonically increasing. For more info, see
        the MIKE+ documentation:
        https://doc.mikepoweredbydhi.help/webhelp/2024/MIKEPlus/MIKEPlus/RiverNetwork_HydrModel/Processed_Data.htm#XREF_52990_Processed_Data:~:text=Note%3A%20The%20conveyance,from%20the%20simulations.
        """
        return tuple(r * A * R ** (2.0 / 3) for r, A, R in zip(resistance, flow_area, radius))

    @property
    def processed(self) -> pd.DataFrame:
        """pandas.DataFrame: The processed cross section data as a pandas DataFrame.

        Examples
        --------
        >>> from mikeio1d.cross_sections import CrossSection
        >>> cs = CrossSection.from_xz([0, 10, 20, 30, 40, 50], [0, 2, 3, 4, 3, 0], location_id="loc1", chainage=100, topo_id="topo1")
        >>> df = cs.processed
        # df DataFrame containing processed cross section data

        >>> df.resistance = df.resistance * 2.0
        >>> cs.processed = df
        # The processed cross section has been updated with the new resistance values

        """
        xs = self._m1d_cross_section
        base_xs = xs.BaseCrossSection
        levels = tuple(base_xs.ProcessedLevels)
        flow_area = tuple(base_xs.ProcessedFlowAreas)
        radius = tuple(base_xs.ProcessedRadii)
        storage_width = tuple(base_xs.ProcessedStorageWidths)
        additional_storage_area = tuple(base_xs.ProcessedAdditionalSurfaceAreas)
        resistance = tuple(base_xs.ProcessedResistanceFactors)
        conveyance_factor = self._calculate_conveyance_factor(resistance, flow_area, radius)
        data = {
            "level": levels,
            "flow_area": flow_area,
            "radius": radius,
            "storage_width": storage_width,
            "additional_storage_area": additional_storage_area,
            "resistance": resistance,
            "conveyance_factor": conveyance_factor,
        }

        df = pd.DataFrame(data)
        return df

    @processed.setter
    def processed(self, df: pd.DataFrame):
        for column_name in [
            "level",
            "flow_area",
            "radius",
            "storage_width",
            "additional_storage_area",
            "resistance",
        ]:
            if column_name not in df.columns:
                raise ValueError(f"Column '{column_name}' is missing from the provided DataFrame.")

        base_xs = self._m1d_cross_section.BaseCrossSection
        base_xs.SetAllProcessedValues(
            df.level.values,
            df.storage_width.values,
            df.flow_area.values,
            df.radius.values,
            df.resistance.values,
            df.additional_storage_area.values,
        )
        self.processed_allow_recompute = False

    @property
    def raw(self) -> pd.DataFrame:
        """pandas.DataFrame: The raw cross section data as a pandas DataFrame.

        Notes
        -----
        The 'marker' column is a comma-separated string of markers at each point.
        The 'marker_labels' column is automatically generated from the 'marker' column
        and does not need to be set when updating marker values.

        Examples
        --------
        >>> from mikeio1d.cross_sections import CrossSection
        >>> cs = CrossSection.from_xz([0, 10, 20, 30, 40, 50], [0, 2, 3, 4, 3, 0], location_id="loc1", chainage=100, topo_id="topo1")
        >>> df = cs.raw
        # df DataFrame containing raw cross section data

        >>> df.z = df.z + 100
        >>> cs.raw = df
        # The raw cross section has been updated with the new z values

        >>> df = cs.raw
        >>> df.loc[0, "markers"] += ",99"
        >>> cs.raw = df
        # Adds a user-defined marker (99) to the first point
        """
        self.recompute_processed()

        data = {
            "markers": [],
            "marker_labels": [],
            "x": [],
            "z": [],
            "resistance": [],
        }

        base_xs = self._m1d_cross_section.BaseCrossSection
        for i, point in enumerate(base_xs.Points):
            markers = [m for m in base_xs.GetMarkersOfPoint(i)]
            data["markers"].append(",".join(str(m) for m in markers))
            data["marker_labels"].append(",".join(Marker.pretty(m) for m in markers))
            data["x"].append(point.X)
            data["z"].append(point.Z)
            data["resistance"].append(point.DistributedResistance)

        return pd.DataFrame(data)

    @raw.setter
    def raw(self, df: pd.DataFrame):
        raw_current: pd.DataFrame = self.raw
        for column_name in raw_current.columns:
            if column_name not in df.columns:
                raise ValueError(f"Column '{column_name}' is missing from the provided DataFrame.")

        base_xs = self._m1d_cross_section.BaseCrossSection
        base_xs.Points.Clear()

        unique_resistances = df.resistance.nunique()
        if unique_resistances == 1:
            self.resistance_distribution == ResistanceDistribution.UNIFORM
            base_xs.FlowResistance.ResistanceValue = float(df.resistance.iloc[0])

        if unique_resistances > 3:
            self.resistance_distribution = ResistanceDistribution.DISTRIBUTED

        for x, z, resistance in zip(df.x, df.z, df.resistance):
            point = CrossSectionPoint(x, z)
            point.DistributedResistance = resistance
            base_xs.Points.Add(point)

        markers_seen = set()
        for i, point in enumerate(base_xs.Points):
            markers_str = df.markers.iloc[i]
            if not markers_str:
                continue

            markers = Marker.list_from_string(markers_str)
            for marker in markers:
                if marker in markers_seen:
                    raise ValueError(f"Duplicate for marker '{marker}'")
                markers_seen.add(marker)
                self._update_marker(marker, i)

        self.recompute_processed()

    def _update_marker(self, marker: int | Marker, point_index: int):
        """Update the marker of the specified point_index."""
        marker = int(marker)
        base_xs = self._m1d_cross_section.BaseCrossSection
        if Marker.is_default_marker(marker):
            base_xs.SetMarkerAt(marker, point_index)
        elif Marker.is_user_marker(marker):
            base_xs.Points[point_index].UserMarker = marker
        else:
            raise ValueError(f"Unknown marker: '{marker}'")

    @property
    def markers(self) -> pd.DataFrame:
        """pandas.DataFrame: The markers of the cross section as a pandas DataFrame.

        Notes
        -----
        Updating markers is more easily done using the 'set_marker' and 'unset_marker' methods.
        The 'marker_label' column is for convenience and does not need to be set.

        Examples
        --------
        >>> from mikeio1d.cross_sections import CrossSection
        >>> cs = CrossSection.from_xz([0, 10, 20, 30, 40, 50], [0, 2, 3, 4, 3, 0], location_id="loc1", chainage=100, topo_id="topo1")
        >>> df = cs.markers
        # df DataFrame containing marker data

        >>> df = df.head(1)
        >>> cs.markers = df
        # The markers of the cross section have been updated to only include the first marker.
        """
        base_xs = self._m1d_cross_section.BaseCrossSection
        markers, marker_indices = base_xs.GetMarkerSequence()

        data = {
            "marker": [],
            "marker_label": [],
            "x": [],
            "z": [],
        }

        for marker, point_index in zip(markers, marker_indices):
            data["marker"].append(marker)
            data["marker_label"].append(Marker.pretty(marker))
            point = base_xs.Points[point_index]
            data["x"].append(point.X)
            data["z"].append(point.Z)

        user_marker_points = (p for p in base_xs.Points if p.UserMarker > 0)
        for point in user_marker_points:
            data["marker"].append(point.UserMarker)
            data["marker_label"].append(Marker.pretty(point.UserMarker))
            data["x"].append(point.X)
            data["z"].append(point.Z)

        return pd.DataFrame(data)

    @markers.setter
    def markers(self, df: pd.DataFrame):
        df_current_markers = self.markers
        for marker in df_current_markers.marker.to_numpy():
            self.unset_marker(marker)
        for _, row in df.iterrows():
            marker, x, z = row.marker, row.x, row.z
            self.set_marker(marker, x, z)

    def set_marker(self, marker: int | Marker, x: float, z: float = None):
        """Set a marker at the point nearest to the specified x, z coordinates.

        Note: if z is not provided, the nearest point in the x direction will be found.

        Parameters
        ----------
        marker : int | Marker
            The marker to set.
        x : float
            The x coordinate of the point.
        z : float (default: None)
            The z coordinate of the point.

        Examples
        --------
        >>> from mikeio1d.cross_sections import Marker
        >>> cs.set_marker(Marker.LEFT_LEVEE_BANK, 10)
        # The LEFT_LEVEE_BANK marker has been set at the point nearest to x=10.

        >>> cs.set_marker(99, 10, 5)
        # A user-defined marker (99) has been set at the point nearest to x=10, z=5.

        """
        point_index = self._find_nearest_point_index(x, z)
        self._update_marker(marker, point_index)

    def unset_marker(self, marker: int | Marker):
        """Remove the specified marker from the cross section.

        Parameters
        ----------
        marker : int | Marker
            The marker to remove.

        Examples
        --------
        >>> cs.unset_marker(99)
        # The user-defined marker (99) has been removed from the cross section.

        >>> cs.unset_marker(Marker.LEFT_LEVEE_BANK)
        # The LEFT_LEVEE_BANK marker has been removed from the cross section.

        """
        marker = int(marker)
        base_xs = self._m1d_cross_section.BaseCrossSection
        base_xs.SetMarkerAt(marker, -1)

    def _find_nearest_point_index(self, x: float, z: float = None) -> int:
        """Find the XSBaseRaw.points index of the nearest point for the given x, z coordinates.

        If z is not provided, the nearest point in the x direction will be found.

        Returns
        -------
        index : int
            The index of the nearest point.

        """
        base_xs = self._m1d_cross_section.BaseCrossSection
        points = base_xs.Points
        points_coords = np.array(tuple((p.X, p.Z) for p in points))
        if z is None:
            distances = np.abs(points_coords[:, 0] - x)
        else:
            distances = np.linalg.norm(points_coords - (x, z), axis=1)

        nearest_index = np.argmin(distances)
        return int(nearest_index)

    def plot(self, ax=None, with_markers: bool = True, with_marker_labels=True, **kwargs):
        """Plot the cross section.

        Parameters
        ----------
        ax : matplotlib.axes.Axes, optional
            The axes to plot to. If not provided, a new figure will be created.
        with_markers : bool, optional
            If True, markers will be plotted.
        with_marker_labels : bool, optional
            If True, marker labels will be plotted. Ignored if with_markers is False.

        Returns
        -------
        ax : matplotlib.axes.Axes
            The axes that was plotted to.

        """
        if ax is None:
            _, ax = plt.subplots()

        df = self.raw

        label = f"'{self.location_id}' @ {self.chainage}"

        ax.plot(df["x"], df["z"], label=label, **kwargs)

        if with_markers:
            mask = df.markers.ne("") & df.markers.notna()
            df_markers = df[mask]
            ax.scatter(df_markers.x, df_markers.z, color="grey", marker="o", zorder=-1)

        if with_markers and with_marker_labels:
            for marker, x, z in zip(df_markers.marker_labels, df_markers.x, df_markers.z):
                ax.annotate(
                    marker,
                    (x, z),
                    textcoords="offset points",
                    xytext=(0, -5),
                    ha="center",
                    fontsize=6,
                )

        ax.set_xlabel("x [meters]")
        ax.set_ylabel("z [meters]")
        ax.grid(True)
        ax.legend()
        ax.set_title("Cross section")

        return ax
