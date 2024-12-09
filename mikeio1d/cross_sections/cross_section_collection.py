"""CrossSectionCollection class."""

from __future__ import annotations

from typing import TYPE_CHECKING

from typing import Dict
from typing import Tuple
from typing import List
from typing import Set

if TYPE_CHECKING:
    import geopandas as gpd

from warnings import warn

from collections.abc import MutableMapping
from pathlib import Path

import pandas as pd

from .cross_section import CrossSection
from .cross_section import Marker

from ..various import try_import_geopandas

from DHI.Mike1D.Generic import Connection
from DHI.Mike1D.Generic import Diagnostics
from DHI.Mike1D.CrossSectionModule import CrossSectionData
from DHI.Mike1D.CrossSectionModule import CrossSectionDataFactory

LocationId = str
Chainage = str
TopoId = str


class CrossSectionCollection(MutableMapping[Tuple[LocationId, Chainage, TopoId], CrossSection]):
    """A collection of CrossSection objects.

    The collection is a dict-like object where the keys are tuples of location ID, chainage and topo ID.

    Parameters
    ----------
    args : list of CrossSection, optional
        A list of CrossSection objects.

    Examples
    --------
    >>> from mikeio1d.cross_sections import CrossSectionCollection, CrossSection
    >>> x = [0, 1, 2, 3, 4, 5]
    >>> z = [0, 1, 2, 3, 4, 5]
    >>> xs1 = CrossSection.from_xz(x, z, location_id="loc1", chainage=100, topo_id="topo1")
    >>> xs2 = CrossSection.from_xz(x, z, location_id="loc2", chainage=200, topo_id="topo1")
    >>> csc = CrossSectionCollection([xs1, xs2])
    # csc is a collection of two cross sections

    """

    def __init__(self, *args, **kwargs):
        self._cross_section_map: dict[tuple[LocationId, Chainage, TopoId], CrossSection] = {}
        self._cross_section_data = CrossSectionData()
        self._cross_section_data_factory = CrossSectionDataFactory()

        if args and isinstance(args[0], list):
            self._handle_args(*args)
        else:
            self._cross_section_map.update(*args, **kwargs)

        self._validate()

    def _handle_args(self, *args):
        if not isinstance(args[0][0], CrossSection):
            raise ValueError("Input must be a list of CrossSection objects")
        for xs in args[0]:
            self[xs.location_id, f"{xs.chainage:.3f}", xs.topo_id] = xs

    def _validate(self):
        for key, cross_section in self.items():
            if key[0] != cross_section.location_id:
                raise ValueError(f"Location ID mismatch: {key[0]} != {cross_section.location_id}")
            if key[1] != f"{cross_section.chainage:.3f}":
                raise ValueError(f"Chainage mismatch: {key[1]} != {cross_section.chainage:.3f}")
            if key[2] != cross_section.topo_id:
                raise ValueError(f"Topo ID mismatch: {key[2]} != {cross_section.topo_id}")

    @staticmethod
    def from_cross_section_data(cross_section_data: CrossSectionData) -> CrossSectionCollection:
        """Create a collection of cross sections from a .NET CrossSectionData object.

        Parameters
        ----------
        cross_section_data : CrossSectionData
            An instance of the .NET object DHI.Mike1D.CrossSectionModule.CrossSectionData

        Returns
        -------
        CrossSectionCollection
            Collection of cross sections.
        """
        csc = CrossSectionCollection()
        csc.initialize_from_cross_section_data(cross_section_data)
        return csc

    def initialize_from_cross_section_data(self, cross_section_data: CrossSectionData):
        """Initialize the collection from a .NET CrossSectionData object."""
        self._cross_section_data = cross_section_data
        for xs in cross_section_data:
            xs = CrossSection(xs)
            self.add_xsection(xs)

    @staticmethod
    def from_xns11(file_name: str | Path) -> CrossSectionCollection:
        """Load a collection of cross sections from an Xns11 file.

        Parameters
        ----------
        file_name : str or Path
            Path to the file to load.

        Returns
        -------
        CrossSectionCollection
            Collection of cross sections.

        Examples
        --------
        >>> from mikeio1d.cross_sections import CrossSectionCollection
        >>> csc = CrossSectionCollection.from_xns11("cross_sections.xns11")
        """
        csc = CrossSectionCollection()
        connection = Connection.Create(str(file_name))
        cross_section_data_factory = CrossSectionDataFactory()
        csc._cross_section_data = cross_section_data_factory.Open(
            connection, Diagnostics("Loading xns11 file.")
        )
        return CrossSectionCollection.from_cross_section_data(csc._cross_section_data)

    def initialize_from_xns11(self, file_name: str | Path):
        """Initialize the collection from an Xns11 file."""
        connection = Connection.Create(str(file_name))
        self._cross_section_data = self._cross_section_data_factory.Open(
            connection, Diagnostics("Loading xns11 file.")
        )
        self.initialize_from_cross_section_data(self._cross_section_data)

    def to_xns11(self, file_name: str | Path, **kwargs):
        """Save the collection to an Xns11 file.

        Parameters
        ----------
        file_name : str or Path
            Path to the file to save.

        Examples
        --------
        >>> from mikeio1d.cross_sections import CrossSectionCollection, CrossSection
        >>> x = [0, 1, 2, 3, 4, 5]
        >>> z = [0, 1, 2, 3, 4, 5]
        >>> xs1 = CrossSection.from_xz(x, z, location_id="loc1", chainage=100, topo_id="topo1")
        >>> xs2 = CrossSection.from_xz(x, z, location_id="loc2", chainage=200, topo_id="topo1")
        >>> csc = CrossSectionCollection([xs1, xs2])
        >>> csc.to_xns11("cross_sections.xns11")
        """
        file_name = self._validate_file_name(file_name)
        self._cross_section_data.Connection = Connection.Create(str(file_name))
        self._cross_section_data_factory.Save(self._cross_section_data)

    def _validate_file_name(self, file_name: str | Path) -> Path:
        if not isinstance(file_name, Path):
            file_name = Path(file_name)
        if not file_name.suffix:
            file_name = file_name.with_suffix(".xns11")
        if file_name.suffix != ".xns11":
            raise ValueError(f"File must have extension .xns11, not {file_name.suffix}")
        return file_name

    def __repr__(self) -> str:
        """Return a string representation of the collection."""
        return f"<CrossSectionCollection {len(self)}>"

    def __getitem__(
        self, key: Tuple[LocationId, Chainage, TopoId]
    ) -> CrossSection | list[CrossSection]:
        """Get a cross section or a collection of cross sections."""
        if isinstance(key, str):
            return self.__getitem__((key, ..., ...))

        if len(key) == 2:
            return self.__getitem__((key[0], key[1], ...))

        if ... in key or slice(None) in key:
            return self._slice_collection(key)
        else:
            return self._cross_section_map.__getitem__(key)

    def _slice_collection(self, key: Tuple[LocationId, Chainage, TopoId]) -> list[CrossSection]:
        return [
            xs
            for k, xs in self._cross_section_map.items()
            if all(
                k_i == key_i or key_i is ... or key_i == slice(None) for k_i, key_i in zip(k, key)
            )
        ]

    def __setitem__(self, key: Tuple[LocationId, Chainage, TopoId], value: CrossSection):
        """Set a cross section in the collection."""
        if not isinstance(value, CrossSection):
            raise ValueError("Value must be a CrossSection object.")
        self._cross_section_data.Add(value._m1d_cross_section)
        return self._cross_section_map.__setitem__(key, value)

    def __delitem__(self, key: Tuple[LocationId, Chainage, TopoId]):
        """Delete a cross section from the collection."""
        xs = self.get(key)
        if xs is not None:
            self._cross_section_data.RemoveCrossSection(xs.location, xs.topo_id)
        return self._cross_section_map.__delitem__(key)

    def __iter__(self):
        """Iterate over the collection."""
        return iter(self._cross_section_map)

    def __len__(self):
        """Return the length of the collection."""
        return len(self._cross_section_map)

    def __or__(self, other) -> CrossSectionCollection:
        """Merge two collections."""
        if isinstance(other, CrossSectionCollection):
            self.update(other)
            return self
        else:
            raise ValueError("Can only merge with another CrossSectionCollection.")

    def _ipython_key_completions_(self):
        """Enable key completions in IPython."""
        return self.keys()

    @property
    def cross_section_data(self) -> CrossSectionData:
        """The DHI.Mike1D.CrossSectionModule.CrossSectionData object."""
        return self._cross_section_data

    def add_xsection(self, xsection: CrossSection):
        """Add a cross section to the collection."""
        location_id = xsection.location_id
        chainage = f"{xsection.chainage:.3f}"
        topo_id = xsection.topo_id
        self[location_id, chainage, topo_id] = xsection

    @property
    def location_ids(self) -> Set[str]:
        """Unique location IDs in the collection."""
        return set([k[0] for k in self.keys()])

    @property
    def chainages(self) -> Set[str]:
        """Unique chainages in the collection (as string with 3 decimals)."""
        return set([k[1] for k in self.keys()])

    @property
    def topo_ids(self) -> Set[str]:
        """Unique topo IDs in the collection."""
        return set([k[2] for k in self.keys()])

    def sel(
        self, location_id: str = ..., chainage: str | float = ..., topo_id: str = ...
    ) -> CrossSection | list[CrossSection]:
        """Select cross sections from the collection.

        Parameters
        ----------
        location_id : str, optional
            Location ID of the cross section.
        chainage : str | float, optional
            Chainage of the cross section.
        topo_id : str, optional
            Topo ID of the cross section.

        Returns
        -------
        CrossSection or list[CrossSection]
            Providing all arguments will return a CrossSection.
            Provinding partial arguments will always return a list, even if it only includes one CrossSection.

        """
        if isinstance(chainage, int) or isinstance(chainage, float):
            chainage = f"{float(chainage):.3f}"
        return self[location_id, chainage, topo_id]

    def plot(self, *args, **kwargs):
        """Plot all cross sections in the collection."""
        for xs in self.values():
            ax = xs.plot(*args, **kwargs)
            kwargs["ax"] = ax
        return ax

    def to_dataframe(self) -> pd.DataFrame:
        """Convert the collection to a DataFrame."""
        location_ids = [k[0] for k in self.keys()]
        chainages = [k[1] for k in self.keys()]
        topo_ids = [k[2] for k in self.keys()]

        df = pd.DataFrame(
            {
                "location_id": location_ids,
                "chainage": chainages,
                "topo_id": topo_ids,
                "cross_section": list(self.values()),
            }
        )
        df = df.set_index(["location_id", "chainage", "topo_id"])
        return df

    def to_geopandas(self, mode="sections") -> gpd.GeoDataFrame:
        """Convert the collection to a GeoDataFrame.

        Parameters
        ----------
        mode : str, optional
            Mode of conversion. Options are "sections" and "markers". Default is "sections".

        Returns
        -------
        gpd.GeoDataFrame
            GeoDataFrame with the cross sections or markers.

        Note:
        ----
        This method requires the geopandas package to be installed.
        Cross sections must have defined coordinates.

        """
        if mode == "sections":
            return self._to_geopandas_sections()
        elif mode == "markers":
            return self._to_geopandas_markers()
        else:
            raise ValueError(f"Unknown mode: {mode}. Options are 'sections' and 'markers'.")

    def _to_geopandas_sections(self) -> gpd.GeoDataFrame:
        try_import_geopandas()
        import geopandas as gpd

        df = self.to_dataframe().reset_index()
        geometries = [xs.geometry.to_shapely() for xs in self.values()]

        data = {
            "location_id": df.location_id,
            "chainage": df.chainage,
            "topo_id": df.topo_id,
            "geometry": geometries,
        }
        gdf = gpd.GeoDataFrame(data=data)
        return gdf

    def _to_geopandas_markers(self) -> gpd.GeoDataFrame:
        """Convert the collection to a GeoDataFrame of the markers as points."""
        try_import_geopandas()
        import geopandas as gpd

        data = {
            "location_id": [],
            "chainage": [],
            "topo_id": [],
            "marker": [],
            "marker_label": [],
            "geometry": [],
        }

        for xs in self.values():
            base_xs = xs._m1d_cross_section.BaseCrossSection
            for i, point in enumerate(base_xs.Points):
                markers = [m for m in base_xs.GetMarkersOfPoint(i)]
                if len(markers) == 0:
                    continue
                data["location_id"].append(xs.location_id)
                data["chainage"].append(xs.chainage)
                data["topo_id"].append(xs.topo_id)
                data["marker"].append(",".join(str(m) for m in markers))
                data["marker_label"].append(",".join(Marker.pretty(m) for m in markers))
                data["geometry"].append(
                    xs.geometry.to_shapely().interpolate(point.X / xs.max_width, normalized=True)
                )

        gdf = gpd.GeoDataFrame(data=data)
        return gdf

    @property
    def interpolation_type(self):
        """Defines how an interpolated cross section is interpolated.

        Returns
        -------
        DHI.Mike1D.CrossSectionModule.XSInterpolationType

            Possible values:
            - ProcessedTopDown: 0
                Interpolates the processed data. Raw data will not be available.
            - Raw: 1
                Interpolates the raw data and calculates processed data from the new raw data.
            - Middling: 2
                Interpolation happens during runtime by requesting values at neighbour cross sections and interpolate between those.

        """
        return self._cross_section_data.XSInterpolationType

    # region Deprecated

    @property
    def xns11(self):
        """Deprecated. Only use CrossSectionCollection instead."""
        warn("Xns11 is deprecated. Use CrossSectionCollection instead.")
        xns11 = getattr(self, "_xns11", None)
        return xns11

    @xns11.setter
    def xns11(self, value):
        warn("Xns11 is deprecated. Use CrossSectionCollection instead.")
        self._xns11 = value

    # endregion
