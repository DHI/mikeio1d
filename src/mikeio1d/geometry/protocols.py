"""Protocols for geometry classes."""

from __future__ import annotations

from typing import Protocol
from shapely.geometry.base import BaseGeometry


class ConvertableToShapely(Protocol):
    """Protocol for classes that can be converted to Shapely geometries."""

    def to_shapely(self) -> BaseGeometry:
        """Convert to a Shapely geometry."""
        ...
