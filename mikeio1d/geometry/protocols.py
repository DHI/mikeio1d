from __future__ import annotations

from typing import Protocol
from shapely.geometry.base import BaseGeometry


class ConvertableToShapely(Protocol):
    def to_shapely(self) -> BaseGeometry:
        ...
