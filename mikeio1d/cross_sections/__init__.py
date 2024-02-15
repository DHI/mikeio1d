from __future__ import annotations

from typing import Dict
from typing import Tuple
from typing import List

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
        return self._m1d_cross_section.TopoID

    @property
    def location_id(self) -> str:
        return self._m1d_cross_section.Location.ID

    @property
    def chainage(self) -> float:
        return self._m1d_cross_section.Location.Chainage

    @property
    def bottom_elevation(self) -> float:
        return self._m1d_cross_section.Location.Z


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
