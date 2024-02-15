from __future__ import annotations

from typing import Dict
from typing import Tuple
from typing import List

import pandas as pd

import matplotlib.pyplot as plt
from IPython.display import display

LocationId = str
Chainage = str
TopoId = str


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

    def read(self) -> pd.DataFrame:
        """
        Read the cross section to a pandas DataFrame.

        Returns
        -------
        df : pandas.DataFrame
            A DataFrame with columns 'x' and 'z'. Units in 'meters'.
        """

        data = {
            "x": [],
            "z": [],
        }

        for point in self._m1d_cross_section.BaseCrossSection.Points:
            data["x"].append(point.X)
            data["z"].append(point.Z)

        return pd.DataFrame(data)

    def plot(self, ax=None, **kwargs):
        """
        Plot the cross section.

        Parameters
        ----------
        ax : matplotlib.axes.Axes, optional
            The axes to plot to. If not provided, a new figure will be created.

        Returns
        -------
        ax : matplotlib.axes.Axes
            The axes that was plotted to.
        """
        is_existing_ax = ax is not None

        if not is_existing_ax:
            _, ax = plt.subplots()

        df = self.read()

        label = f"'{self.location_id}' @ {self.chainage}"
        ax.plot(df["x"], df["z"], label=label, **kwargs)
        ax.set_xlabel("x [meters]")
        ax.set_ylabel("z [meters]")
        ax.grid(True)
        ax.set_title("Cross section")
        ax.legend()

        if is_existing_ax:
            display(ax.figure)

        return ax


class CrossSectionCollection(Dict[Tuple[LocationId, Chainage, TopoId], CrossSection]):
    def __init__(self):
        super().__init__()

    def __repr__(self) -> str:
        return "<CrossSectionCollection>"

    def __getitem__(
        self, key: Tuple[LocationId, Chainage, TopoId]
    ) -> CrossSection | List[CrossSection]:
        if isinstance(key, str):
            return self.__getitem__((key, ..., ...))

        if len(key) == 2:
            return self.__getitem__((key[0], key[1], ...))

        if ... in key:
            return [
                v
                for k, v in self.items()
                if all(k_i == key_i or key_i is ... for k_i, key_i in zip(k, key))
            ]
        else:
            return super().__getitem__(key)

    def add_xsection(self, xsection: CrossSection):
        location_id = xsection.location_id
        chainage = f"{xsection.chainage:.3f}"
        topo_id = xsection.topo_id
        self[location_id, chainage, topo_id] = xsection
