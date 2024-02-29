from __future__ import annotations

from typing import TYPE_CHECKING
from warnings import warn

if TYPE_CHECKING:
    from typing import Iterable
    from typing import Tuple
    from typing import List
    from ..geometry import CrossSectionGeometry

import numpy as np

from enum import Enum

import pandas as pd

import matplotlib.pyplot as plt

from ..various import try_import_shapely
from .cross_section_factory import CrossSectionFactory

import System
from DHI.Mike1D.CrossSectionModule import CrossSectionPoint
from DHI.Mike1D.Generic import ProcessingOption
from DHI.Mike1D.Generic import ResistanceDistribution
from DHI.Mike1D.Generic import ResistanceFormulation


class Marker(Enum):
    LEFT_LEVEE_BANK = 1
    LOWEST_POINT = 2
    RIGHT_LEVEE_BANK = 3
    LEFT_LOW_FLOW_BANK = 4
    RIGHT_LOW_FLOW_BANK = 5

    def __repr__(self) -> str:
        return Marker.pretty(self)

    def __int__(self) -> int:
        return self.value

    @staticmethod
    def is_default_marker(marker: int | Marker) -> bool:
        return marker in Marker

    @staticmethod
    def is_user_marker(marker: int | Marker) -> bool:
        MIN_USER_MARKER = 8
        return marker >= MIN_USER_MARKER

    @staticmethod
    def pretty(marker: int | Marker) -> str:
        if Marker.is_default_marker(marker):
            marker = marker if isinstance(marker, Marker) else Marker(marker)
            return marker.name.replace("_", " ").title() + f" ({marker.value})"
        elif Marker.is_user_marker(marker):
            return f"User Marker ({marker})"
        else:
            return f"Unknown Marker ({marker})"

    @staticmethod
    def from_pretty(marker: str) -> int:
        marker = int(marker.split("(")[-1][:-1])
        return marker

    @staticmethod
    def list_from_string(s: str) -> List[int]:
        return [int(m) for m in s.split(",")]


class CrossSection:
    def __init__(self, m1d_cross_section):
        if hasattr(m1d_cross_section, "__implementation__"):
            m1d_cross_section = m1d_cross_section.__implementation__

        self._m1d_cross_section = m1d_cross_section

    @staticmethod
    def create_from_xz(
        xz_data: pd.DataFrame | np.ndarray | Iterable[Iterable[float, float]],
        location_id: str,
        chainage: float,
        topo_id: str,
        default_markers: bool = True,
    ) -> CrossSection:
        """
        Create an open cross section from xz data.

        Parameters
        ----------
        xz_data : pandas.DataFrame | numpy.ndarray | iterable of x, z pairs
            If a DataFrame, it must have columns 'x' and 'z' (lowercase)
            If a numpy array, it must have shape (n, 2).
            If an iterable, it must yield iterables of length 2.
        location_id : str
            Location ID of the cross section.
        chainage : float
            Chainage of the cross section.
        topo_id : str
            Topo ID of the cross section.

        Returns
        -------
        cross_section : CrossSection
        """
        if isinstance(xz_data, pd.DataFrame):
            x = xz_data["x"]
            z = xz_data["z"]
        else:
            x, z = zip(*xz_data)

        m1d_cross_section = CrossSectionFactory.create_open_from_xz_data(
            x, z, location_id, chainage, topo_id, default_markers
        )
        return CrossSection(m1d_cross_section)

    def __repr__(self) -> str:
        return f"<CrossSection: {self.location_id}, {format(self.chainage, '.3f')}, {self.topo_id}>"

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
    def bottom_level(self) -> float:
        return self._m1d_cross_section.BottomLevel

    @property
    def height(self) -> float:
        """Height of the cross section."""
        return self._m1d_cross_section.Height

    @property
    def interpolated(self) -> bool:
        """Is the cross section interpolated? (i.e. not measured)"""
        return self._m1d_cross_section.Interpolated

    @property
    def is_open(self) -> bool:
        """Is the cross section open? (i.e. not closed)"""
        return self._m1d_cross_section.IsOpen

    @property
    def max_width(self) -> float:
        """Maximum width of the cross section."""
        return self._m1d_cross_section.MaximumWidth

    @property
    def min_water_depth(self) -> float:
        """
        Minimum water depth of the cross section.
        If the water depth goes below this depth, it will be corrected to match this depth.

        This can be negative, in case the cross section has a slot attached.
        """
        return self._m1d_cross_section.MinWaterDepth

    @property
    def resistance_factor_proportionality(self) -> float:
        """
        A proportionality factor that is multiplied with the resistance factor.

        ResistanceFactorProportionality is used by the resistance factor boundaries to adjust the resistance factor during the simulation.
        """
        return self._m1d_cross_section.ResistanceFactorProportionality

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
        """The geometry of the cross section."""
        try_import_shapely()
        from ..geometry import CrossSectionGeometry

        return CrossSectionGeometry(self._m1d_cross_section)

    @property
    def resistance_type(self):
        """
        Get the type of resistance used in the cross section.

        Parameters
        ----------
        resistance_type: int
            The type of resistance used in the cross section:

            0 - Relative

            1 - Manning's n

            2 - Manning's M

            3 - Chezy number

            4 - Darcy-Weisbach

            5 - Colebrook White

            6 - Hazen Williams


        Returns
        -------
        DHI.Mike1D.Generic.ResistanceFormulation
            The type of resistance used in the cross section.
        """
        return self._m1d_cross_section.BaseCrossSection.FlowResistance.Formulation

    @resistance_type.setter
    def resistance_type(self, value: int):
        self._m1d_cross_section.BaseCrossSection.FlowResistance.Formulation = ResistanceFormulation(
            value
        )

    @property
    def resistance_distribution(self):
        """
        Get the distribution of resistance used in the cross section.

        Parameters
        ----------
        The resistance distribution is represented by an integer value:

        0 - Uniform

        1 - Zones

        2 - Distributed

        3 - Constant

        4 - ExponentVarying


        Returns
        -------
        str
            The distribution of resistance used in the cross section.

        Notes
        -----
        The resistance distribution is represented by an integer value:
        0 - Uniform
        1 - Zones
        2 - Distributed
        3 - Constant
        4 - ExponentVarying
        """
        return self._m1d_cross_section.BaseCrossSection.FlowResistance.ResistanceDistribution

    @resistance_distribution.setter
    def resistance_distribution(self, value: int):
        value = int(value)
        self._m1d_cross_section.BaseCrossSection.FlowResistance.ResistanceDistribution = (
            ResistanceDistribution(value)
        )

    def _calculate_conveyance_factor(
        self, resistance: Tuple[float], flow_area: Tuple[float], radius: Tuple[float]
    ) -> Tuple[float]:
        """
        Calculate the conveyance factor from resistance, flow area and radius.

        Note that this is not the true conveyance factor since resistance could be relative. However,
        this is the same calculation provided by MIKE+ cross section editor. Its main purpose is for checking
        that conveyance values will be monotonically increasing. For more info, see
        the MIKE+ documentation:
        https://doc.mikepoweredbydhi.help/webhelp/2024/MIKEPlus/MIKEPlus/RiverNetwork_HydrModel/Processed_Data.htm#XREF_52990_Processed_Data:~:text=Note%3A%20The%20conveyance,from%20the%20simulations.
        """
        return tuple(r * A * R ** (2.0 / 3) for r, A, R in zip(resistance, flow_area, radius))

    def _warn_if_resistance_distribution_is_not_zones(self):
        if self.resistance_distribution != ResistanceDistribution.Zones:
            message = (
                "You are accessing/setting zone resistances without the correct resistance distribution type. "
                "Set the resistance distribution type to zones by setting '.resistance_distribution' to 1."
            )
            warn(message)

    @property
    def resistance_left_high_flow(self) -> float:
        self._warn_if_resistance_distribution_is_not_zones()
        return self._m1d_cross_section.BaseCrossSection.FlowResistance.ResistanceLeftHighFlow

    @resistance_left_high_flow.setter
    def resistance_left_high_flow(self, value: float):
        self._warn_if_resistance_distribution_is_not_zones()
        self._m1d_cross_section.BaseCrossSection.FlowResistance.ResistanceLeftHighFlow = value

    @property
    def resistance_low_flow(self):
        self._warn_if_resistance_distribution_is_not_zones()
        return self._m1d_cross_section.BaseCrossSection.FlowResistance.ResistanceLowFlow

    @resistance_low_flow.setter
    def resistance_low_flow(self, value: float):
        self._warn_if_resistance_distribution_is_not_zones()
        self._m1d_cross_section.BaseCrossSection.FlowResistance.ResistanceLowFlow = value

    @property
    def resistance_right_high_flow(self):
        self._warn_if_resistance_distribution_is_not_zones()
        return self._m1d_cross_section.BaseCrossSection.FlowResistance.ResistanceRightHighFlow

    @resistance_right_high_flow.setter
    def resistance_right_low_flow(self, value: float):
        self._warn_if_resistance_distribution_is_not_zones()
        self._m1d_cross_section.BaseCrossSection.FlowResistance.ResistanceRightHighFlow = value

    @property
    def number_of_processing_levels(self) -> int:
        """
        The number of levels used in the processed data. Setting this will recalculate
        processed data with equidistant levels based on the specified integer.
        """
        pls = self._m1d_cross_section.BaseCrossSection.ProcessingLevelsSpecs
        return pls.NoOfLevels

    @number_of_processing_levels.setter
    def number_of_processing_levels(self, value: int):
        pls = self._m1d_cross_section.BaseCrossSection.ProcessingLevelsSpecs
        pls.Option = ProcessingOption.EquidistantLevels
        pls.NoOfLevels = value
        self._m1d_cross_section.BaseCrossSection.CalculateProcessedData()

    @property
    def processing_levels(self) -> Tuple[float]:
        """
        The levels used in the processed data. Setting this will recalculate the processed
        data using only the specified levels. The minimum and maximum levels will be automatically
        added if not already present.
        """
        return tuple(self._m1d_cross_section.BaseCrossSection.ProcessedLevels)

    @processing_levels.setter
    def processing_levels(self, levels: Iterable[float]):
        pls = self._m1d_cross_section.BaseCrossSection.ProcessingLevelsSpecs
        pls.Option = ProcessingOption.UserDefinedLevels
        pls.UserDefLevels = tuple(levels)
        self._m1d_cross_section.BaseCrossSection.CalculateProcessedData()

    @property
    def processed_allow_recompute(self) -> bool:
        """
        Whether the processed data can be recomputed (e.g. if the raw data has changed).

        Default is True.
        """
        return not self._m1d_cross_section.BaseCrossSection.ProcessedDataProtected

    @processed_allow_recompute.setter
    def processed_allow_recompute(self, value: bool):
        self._m1d_cross_section.BaseCrossSection.ProcessedDataProtected = not value

    def recompute_processed(self):
        """
        Recompute the processed data.

        In most cases this is not necessary as it will be done automatically when the raw data changes.
        If processed_allow_recompute is set to False, then this will do nothing.
        """
        self._m1d_cross_section.BaseCrossSection.CalculateProcessedData()

    @property
    def processed(self) -> pd.DataFrame:
        """
        Read the processed cross section to a pandas DataFrame.

        Returns
        -------
        df : pandas.DataFrame
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
        """
        Read the cross section to a pandas DataFrame.

        Returns
        -------
        df : pandas.DataFrame
            A DataFrame with columns 'x' and 'z'. Units in 'meters'.
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
        """
        Set the raw cross section from a DataFrame.

        Parameters
        ----------
        df : pandas.DataFrame
            A DataFrame with the same shape and column headers as the output of the raw property.
        """
        raw_current: pd.DataFrame = self.raw
        for column_name in raw_current.columns:
            if column_name not in df.columns:
                raise ValueError(f"Column '{column_name}' is missing from the provided DataFrame.")

        base_xs = self._m1d_cross_section.BaseCrossSection
        base_xs.Points.Clear()

        unique_resistances = df.resistance.nunique()
        if unique_resistances == 1:
            self.resistance_distribution == ResistanceDistribution.Uniform
            base_xs.FlowResistance.ResistanceValue = float(df.resistance.iloc[0])

        if unique_resistances > 3:
            self.resistance_distribution = ResistanceDistribution.Distributed

        for x, z, resistance in zip(df.x, df.z, df.resistance):
            point = CrossSectionPoint(x, z)
            point.DistributedResistance = resistance
            base_xs.Points.Add(point)

        for i, point in enumerate(base_xs.Points):
            markers_str = df.markers.iloc[i]
            if not markers_str:
                continue

            markers = Marker.list_from_string(markers_str)
            for marker in markers:
                self._update_marker(marker, i)

        self.recompute_processed()

    def _update_marker(self, marker: int | Marker, point_index: int):
        """
        Update the marker of the specified point_index.
        """
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
        """
        Get the markers of the cross section.

        Returns
        -------
        df : pandas.DataFrame
            A DataFrame with columns 'x', 'z', 'marker', and 'marker_label'.
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
        for marker in df_current_markers.marker.values:
            self.unset_marker(marker)
        for _, row in df.iterrows():
            marker, x, z = row.marker, row.x, row.z
            self.set_marker(marker, x, z)

    def set_marker(self, marker: int | Marker, x: float, z: float = 0):
        """
        Set a marker at the point nearest to the specified x, z coordinates.

        Note: snapping to nearest point is 1000x more sensitive to 'x' than 'z'.

        Parameters
        ----------
        marker : int | Marker
            The marker to set.
        x : float
            The x coordinate of the point.
        z : float (default: 0.0)
            The z coordinate of the point.
        """
        point_index = self._find_nearest_point_index(x, z)
        self._update_marker(marker, point_index)

    def unset_marker(self, marker: int | Marker):
        """
        Removes the specified marker from the cross section.

        Parameters
        ----------
        marker : int | Marker
            The marker to remove.
        """
        marker = int(marker)
        base_xs = self._m1d_cross_section.BaseCrossSection
        base_xs.SetMarkerAt(marker, -1)

    def _find_nearest_point_index(self, x: float, z: float = 0) -> int:
        """
        Find the XSBaseRaw.points index of the nearest point for the given x, z coordinates.

        Note: 'x' is weighted 1000 times more than 'z' to make the search more sensitive to x differences.

        Returns
        -------
        index : int
            The index of the nearest point.
        """
        base_xs = self._m1d_cross_section.BaseCrossSection
        points = base_xs.Points
        points_coords = np.array(tuple((p.X, p.Z) for p in points))
        weights = np.array([1000, 1])  # Higher weight for x difference
        distances = np.linalg.norm((points_coords - (x, z)) * weights, axis=1)
        nearest_index = np.argmin(distances)
        return int(nearest_index)

    def plot(self, ax=None, with_markers: bool = True, with_marker_labels=True, **kwargs):
        """
        Plot the cross section.

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
