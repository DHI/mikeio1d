from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..geometry import CrossSectionGeometry

from enum import Enum

import pandas as pd

import matplotlib.pyplot as plt

from ..various import try_import_shapely


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


class CrossSection:
    def __init__(self, m1d_cross_section):
        self._m1d_cross_section = m1d_cross_section.__implementation__

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

    def read(self) -> pd.DataFrame:
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
        }

        base_xs = self._m1d_cross_section.BaseCrossSection
        for i, point in enumerate(base_xs.Points):
            markers = [m for m in base_xs.GetMarkersOfPoint(i)]
            data["markers"].append(",".join(str(m) for m in markers))
            data["marker_labels"].append(",".join(Marker.pretty(m) for m in markers))
            data["x"].append(point.X)
            data["z"].append(point.Z)

        return pd.DataFrame(data)

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

        df = self.read()

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
