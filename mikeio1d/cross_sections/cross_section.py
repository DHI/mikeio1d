from __future__ import annotations

from typing import TYPE_CHECKING

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

from DHI.Mike1D.CrossSectionModule import CrossSectionPoint
from DHI.Mike1D.Generic import ProcessingOption


class Marker(Enum):
    LEFT_LEVEE_BANK = 1
    LOWEST_POINT = 2
    RIGHT_LEVEE_BANK = 3
    LEFT_LOW_FLOW_BANK = 4
    RIGHT_LOW_FLOW_BANK = 5

    def __repr__(self) -> str:
        return Marker.pretty(self)

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
    def list_from_string(s: str) -> List[Marker]:
        return [Marker(int(m)) for m in s.split(",")]


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
            x, z, location_id, chainage, topo_id
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
    def resistance_type(self) -> str:
        """The type of resistance used in the cross section."""
        return self._m1d_cross_section.ResistanceFormulation

    @property
    def resistance_distribution(self) -> str:
        """The distribution of resistance used in the cross section."""
        return self._m1d_cross_section.BaseCrossSection.FlowResistance.ResistanceDistribution

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
                if Marker.is_default_marker(marker):
                    base_xs.SetMarkerAt(marker.value, i)
                elif Marker.is_user_marker(marker):
                    point.UserMarker = marker.value
                else:
                    raise ValueError(f"Unknown marker: '{marker}'")

        base_xs.CalculateProcessedData()

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
