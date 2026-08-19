"""Package for derived quantities."""

from .default_quantities import get_default_derived_quantity_classes
from .derived_quantity import DerivedQuantity

__all__ = ["DerivedQuantity", "get_default_derived_quantity_classes"]
