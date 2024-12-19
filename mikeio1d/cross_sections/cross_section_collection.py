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
from collections.abc import Collection
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
    cross_sections: Collection[CrossSection] or CrossSectionData or Path or str, optional
        If Collection[CrossSection], the collection will be initialized from the list of CrossSection objects.
        If CrossSectionData, the collection will be initialized from a .NET DHI.Mike1D.CrossSectionModule.CrossSectionData object.
        If Path or str, the collection will be initialized from an xns11 file.


    Examples
    --------
    # Create a collection from a list of cross sections
    >>> from mikeio1d.cross_sections import CrossSectionCollection, CrossSection
    >>> x = [0, 1, 2, 3, 4, 5]
    >>> z = [0, 1, 2, 3, 4, 5]
    >>> xs1 = CrossSection.from_xz(x, z, location_id="loc1", chainage=100, topo_id="topo1")
    >>> xs2 = CrossSection.from_xz(x, z, location_id="loc2", chainage=200, topo_id="topo1")
    >>> csc = CrossSectionCollection([xs1, xs2])

    # Access a cross section with indexing, or explicitly with sel()
    >>> csc['loc1', '100.000', 'topo1']
    >>> csc.sel(location_id='loc1', chainage=100, topo_id='topo1')

    # Create a collection from an xns11 file
    >>> csc = CrossSectionCollection("cross_sections.xns11")

    # Save the collection to an xns11 file
    >>> csc.to_xns11("cross_sections.xns11")
    """

    def __init__(
        self, cross_sections: Collection[CrossSection] | CrossSectionData | Path | str = None
    ):
        self._cross_section_map: dict[tuple[LocationId, Chainage, TopoId], CrossSection] = {}
        self._cross_section_data = CrossSectionData()
        self._cross_section_data_factory = CrossSectionDataFactory()

        if cross_sections is None:
            return

        if isinstance(cross_sections, CrossSectionData):
            self._init_from_cross_section_data(cross_sections)
        elif isinstance(cross_sections, Path) or isinstance(cross_sections, str):
            self._init_from_xns11(cross_sections)
        elif isinstance(cross_sections, Collection):
            self._init_from_cross_section_list(cross_sections)
        else:
            raise ValueError("Invalid parameter for 'cross_sections'.")

    def _init_from_cross_section_list(self, cross_sections: Collection[CrossSection]):
        """Initialize the collection from a list of CrossSection objects."""
        for xs in cross_sections:
            self.add(xs)

    def _init_from_cross_section_data(self, cross_section_data: CrossSectionData):
        """Initialize the collection from a .NET CrossSectionData object."""
        self._cross_section_data = cross_section_data
        for xs in cross_section_data:
            xs = CrossSection(xs)
            location_id = xs.location_id
            chainage = self._convert_chainage_to_str(xs.chainage)
            topo_id = xs.topo_id
            self._cross_section_map[(location_id, chainage, topo_id)] = xs

    def _init_from_xns11(self, file_name: str | Path):
        """Initialize the collection from an Xns11 file."""
        file_name = self._validate_file_name(file_name)
        if not file_name.exists():
            raise FileNotFoundError(f"File not found: {file_name}")
        connection = Connection.Create(str(file_name))
        self._cross_section_data = self._cross_section_data_factory.Open(
            connection, Diagnostics("Loading xns11 file.")
        )
        self._init_from_cross_section_data(self._cross_section_data)

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
        return f"<mikeio1d.{type(self).__name__} ({len(self)})>"

    def __getitem__(
        self, key: Tuple[LocationId, Chainage, TopoId]
    ) -> CrossSection | list[CrossSection]:
        """Get a cross section or a collection of cross sections."""
        if isinstance(key, str):
            return self.__getitem__((key, ..., ...))

        if len(key) == 2:
            return self.__getitem__((key[0], key[1], ...))

        key = self._validate_key(key)

        if ... in key or slice(None) in key:
            return self._slice_collection(key)
        else:
            return self._cross_section_map.__getitem__(key)

    def _validate_key(
        self, key: Tuple[LocationId, Chainage, TopoId]
    ) -> Tuple[LocationId, Chainage, TopoId]:
        """Validate a key."""
        if len(key) != 3:
            raise ValueError("Key must be a tuple of Location ID, Chainage and Topo ID.")

        location_id, chainage, topo_id = key

        if chainage is not ... and chainage != slice(None):
            chainage = self._convert_chainage_to_str(chainage)

        return (location_id, chainage, topo_id)

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
        key = self._validate_key_value_pair(key, value)
        if key in self._cross_section_map:
            del self[key]
        self._cross_section_data.Add(value._m1d_cross_section)
        return self._cross_section_map.__setitem__(key, value)

    def _validate_key_value_pair(
        self, key: Tuple[LocationId, Chainage, TopoId], value: CrossSection
    ) -> Tuple[LocationId, Chainage, TopoId]:
        """Validate a key and CrossSection pair."""
        location_id, chainage, topo_id = self._validate_key(key)
        if not isinstance(value, CrossSection):
            raise ValueError("Value must be a CrossSection object.")
        if location_id != value.location_id:
            raise ValueError(
                f"Location ID of key does not match Location ID of CrossSection ({location_id} != {value.location_id})"
            )
        xs_chainage = self._convert_chainage_to_str(value.chainage)
        if chainage != xs_chainage:
            raise ValueError(
                f"Chainage of key does not match Chainage of CrossSection ({chainage} != {xs_chainage})"
            )
        if topo_id != value.topo_id:
            raise ValueError(
                f"Topo ID of key does not match Topo ID of CrossSection ({topo_id} != {value.topo_id})"
            )
        return (location_id, chainage, topo_id)

    def _convert_chainage_to_str(self, chainage: float | int) -> str:
        """Convert a chainage to a string with 3 decimals."""
        return f"{float(chainage):.3f}"

    def __delitem__(self, key: Tuple[LocationId, Chainage, TopoId]):
        """Delete a cross section from the collection."""
        key = self._validate_key(key)
        xs = self.get(key)
        if xs is not None:
            deleted = self._cross_section_data.RemoveCrossSection(xs.location, xs.topo_id)
            if not deleted:
                raise ValueError(f"Cross section not found: {key}")
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

    @property
    def data(self) -> CrossSectionData:
        """The DHI.Mike1D.CrossSectionModule.CrossSectionData object.

        Alias for 'cross_section_data' property.
        """
        return self._cross_section_data

    def add(self, cross_section: CrossSection):
        """Add a cross section to the collection.

        Parameters
        ----------
        cross_section : CrossSection
            Cross section to add.
        """
        location_id = cross_section.location_id
        chainage = self._convert_chainage_to_str(cross_section.chainage)
        topo_id = cross_section.topo_id
        self[location_id, chainage, topo_id] = cross_section

    def remove(self, cross_section: CrossSection):
        """Remove a cross section from the collection.

        Parameters
        ----------
        cross_section : CrossSection
            Cross section to remove.
        """
        location_id = cross_section.location_id
        chainage = self._convert_chainage_to_str(cross_section.chainage)
        topo_id = cross_section.topo_id
        del self[location_id, chainage, topo_id]

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
            chainage = self._convert_chainage_to_str(chainage)
        return self[location_id, chainage, topo_id]

    def to_xns11(self, file_name: str | Path, **kwargs):
        """Save the collection to an Xns11 file.

        Parameters
        ----------
        file_name : str or Path
            Path to the file to save.

        Examples
        --------
        >>> csc.to_xns11("cross_sections.xns11")
        """
        file_name = self._validate_file_name(file_name)
        self._cross_section_data.Connection = Connection.Create(str(file_name))
        self._cross_section_data_factory.Save(self._cross_section_data)

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

    def to_geopandas(self, mode: str = "sections") -> gpd.GeoDataFrame:
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
                if xs.max_width is None or xs.max_width == 0:
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
