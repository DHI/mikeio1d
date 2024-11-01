"""Contains a helper function to get a list of all derived quantity classes in this package."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from typing import List
    from typing import Type

import pkgutil
import inspect
import importlib

from ..derived_quantity import DerivedQuantity


def get_default_derived_quantity_classes() -> List[Type[DerivedQuantity]]:
    """Get list of all derived quantity classes in this package."""
    derived_quantity_classes = []
    for importer, modname, ispkg in pkgutil.iter_modules(__path__):
        module = importlib.import_module("." + modname, __name__)
        for name, obj in inspect.getmembers(module):
            if (
                inspect.isclass(obj)
                and issubclass(obj, DerivedQuantity)
                and obj is not DerivedQuantity
            ):
                derived_quantity_classes.append(obj)
    return derived_quantity_classes
