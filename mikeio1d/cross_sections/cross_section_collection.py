from __future__ import annotations

from typing import TYPE_CHECKING

from typing import Dict
from typing import Tuple
from typing import List

if TYPE_CHECKING:
    import geopandas as gpd

from .cross_section import CrossSection

from ..various import try_import_geopandas

LocationId = str
Chainage = str
TopoId = str


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

    def sel(
        self, location_id: str = ..., chainage: str = ..., topo_id: str = ...
    ) -> CrossSection | List[CrossSection]:
        """
        This method is used to select cross sections from the collection.

        Parameters
        ----------
        location_id : str, optional
            Location ID of the cross section.
        chainage : str, optional
            Chainage of the cross section, with three decimals.
        topo_id : str, optional
            Topo ID of the cross section.

        Returns
        -------
        CrossSection or list of CrossSection
            Providing all arguments will return a CrossSection.
            Provinding partial arguments will always return a list, even if it only has one CrossSection.
        """
        return self[location_id, chainage, topo_id]

    def to_geopandas(self) -> gpd.GeoDataFrame:
        try_import_geopandas()
        import geopandas as gpd

        geometries = [xs.geometry.to_shapely() for xs in self.values()]
        gdf = gpd.GeoDataFrame(geometry=geometries)
        return gdf

    def add_xsection(self, xsection: CrossSection):
        location_id = xsection.location_id
        chainage = f"{xsection.chainage:.3f}"
        topo_id = xsection.topo_id
        self[location_id, chainage, topo_id] = xsection
