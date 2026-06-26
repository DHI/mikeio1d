"""Package for derived quantities."""

from .derived_quantity import DerivedQuantity
from .default_quantities import get_default_derived_quantity_classes

__all__ = ["DerivedQuantity", "get_default_derived_quantity_classes"]
