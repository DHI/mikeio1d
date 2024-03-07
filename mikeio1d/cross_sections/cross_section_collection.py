from __future__ import annotations

from typing import TYPE_CHECKING

from typing import Dict
from typing import Tuple
from typing import List
from typing import Set

if TYPE_CHECKING:
    import geopandas as gpd

    from ..xns11 import Xns11

import pandas as pd

from .cross_section import CrossSection
from .cross_section import Marker

from ..various import try_import_geopandas

LocationId = str
Chainage = str
TopoId = str


class CrossSectionCollection(Dict[Tuple[LocationId, Chainage, TopoId], CrossSection]):
    """
    A collection of CrossSection objects.

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
        if args and isinstance(args[0], list):
            self._handle_args(*args)
        else:
            super().__init__(*args, **kwargs)

        self.xns11: Xns11 | None = None

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

    def __repr__(self) -> str:
        return f"<CrossSectionCollection {len(self)}>"

    def __getitem__(
        self, key: Tuple[LocationId, Chainage, TopoId]
    ) -> CrossSection | CrossSectionCollection:
        if isinstance(key, str):
            return self.__getitem__((key, ..., ...))

        if len(key) == 2:
            return self.__getitem__((key[0], key[1], ...))

        if ... in key or slice(None) in key:
            return self._slice_collection(key)
        else:
            return super().__getitem__(key)

    def _slice_collection(self, key: Tuple[LocationId, Chainage, TopoId]) -> CrossSectionCollection:
        return CrossSectionCollection(
            {
                k: xs
                for k, xs in self.items()
                if all(
                    k_i == key_i or key_i is ... or key_i == slice(None)
                    for k_i, key_i in zip(k, key)
                )
            }
        )

    def __or__(self, other) -> CrossSectionCollection:
        if isinstance(other, CrossSectionCollection):
            return CrossSectionCollection({**self, **other})
        else:
            super().__or__(other)

    def add_xsection(self, xsection: CrossSection):
        """
        Add a cross section to the collection.
        """
        location_id = xsection.location_id
        chainage = f"{xsection.chainage:.3f}"
        topo_id = xsection.topo_id
        self[location_id, chainage, topo_id] = xsection

        if self.xns11:
            self.xns11._cross_section_data.Add(xsection._m1d_cross_section)

    @property
    def location_ids(self) -> Set[str]:
        """
        Unique location IDs in the collection.
        """
        return set([k[0] for k in self.keys()])

    @property
    def chainages(self) -> Set[str]:
        """
        Unique chainages in the collection (as string with 3 decimals).
        """
        return set([k[1] for k in self.keys()])

    @property
    def topo_ids(self) -> Set[str]:
        """
        Unique topo IDs in the collection.
        """
        return set([k[2] for k in self.keys()])

    def sel(
        self, location_id: str = ..., chainage: str | float = ..., topo_id: str = ...
    ) -> CrossSection | List[CrossSection]:
        """
        This method is used to select cross sections from the collection.

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
        CrossSection or list of CrossSection
            Providing all arguments will return a CrossSection.
            Provinding partial arguments will always return a list, even if it only has one CrossSection.
        """
        if isinstance(chainage, int) or isinstance(chainage, float):
            chainage = f"{float(chainage):.3f}"
        return self[location_id, chainage, topo_id]

    def plot(self, *args, **kwargs):
        for xs in self.values():
            ax = xs.plot(*args, **kwargs)
            kwargs["ax"] = ax
        return ax

    def to_dataframe(self) -> pd.DataFrame:
        """
        Converts the collection to a DataFrame.
        """
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

    def to_geopandas(self) -> gpd.GeoDataFrame:
        """
        Converts the collection to a GeoDataFrame.

        Note
        ----
        This method requires the geopandas package to be installed.
        Cross sections must have defined coordinates.
        """
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

    def to_geopandas_markers(self) -> gpd.GeoDataFrame:
        """
        Converts the collection to a GeoDataFrame of the markers as points.
        """
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
