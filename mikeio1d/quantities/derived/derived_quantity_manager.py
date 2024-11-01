"""DerivedQuantityManager class."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from typing import List
    from typing import Dict
    from mikeio1d.res1d import Res1D

from .derived_quantity import DerivedQuantity
from .default_quantities import default_derived_quantities

DerivedQuantityName = str


class DerivedQuantityManager:
    """The derived quantity manager. Use this to register and unregister derived quantities."""

    _instance = None

    def __new__(cls):
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        self._derived_quantities: Dict[DerivedQuantityName, DerivedQuantity] = {}

    @property
    def derived_quantities(self) -> Dict[DerivedQuantityName, DerivedQuantity]:
        """Get the derived quantities."""
        return self._derived_quantities

    def register(self, derived_quantity: type[DerivedQuantity]):
        """Register a derived quantity."""
        if derived_quantity._NAME in self._derived_quantities:
            raise ValueError(
                f"Derived quantity with name '{derived_quantity._NAME}' already exists."
            )
        self._derived_quantities[derived_quantity._NAME] = derived_quantity

    def unregister(self, derived_quantity_name: str):
        """Unregister a derived quantity."""
        self._derived_quantities.pop(derived_quantity_name, None)

    def get_quantity_where(
        self, res1d: Res1D, source_quantity: str, group: str
    ) -> List[DerivedQuantity]:
        """Get derived quantities matching criteria."""
        return [
            q(res1d)
            for q in self._derived_quantities.values()
            if q._SOURCE_QUANTITY == source_quantity and group in q._GROUPS
        ]

    @staticmethod
    def create_default_manager():
        """Create a default derived quantity manager."""
        derived_quantity_manager = DerivedQuantityManager()
        for dq in default_derived_quantities:
            derived_quantity_manager.register(dq)
        return derived_quantity_manager
