from __future__ import annotations

from typing import TYPE_CHECKING

from typing import Dict

if TYPE_CHECKING:  # pragma: no cover
    from typing import List
    from typing import Optional

    import pandas as pd

    from ..res1d import Res1D
    from .result_location import ResultLocation
    from .result_quantity import ResultQuantity
    from ..result_reader_writer.result_reader import ColumnMode
    from ..quantities import TimeSeriesIdGroup

import pandas as pd

from .result_location import ResultLocation
from .result_quantity import ResultQuantity

from ..dotnet import pythonnet_implementation as impl
from .result_quantity_collection import ResultQuantityCollection
from .various import make_proper_variable_name
from .various import build_html_repr_from_sections
from .result_quantity_derived_collection import ResultQuantityDerivedCollection
from ..quantities import DerivedQuantity


class ResultLocations(Dict[str, ResultLocation]):
    """
    A base class for a network locations (nodes, reaches)
    or a catchments wrapper class.

    Parameters
    ----------
    res1d : Res1D
        Res1D object the result location belongs to.

    Attributes
    ----------
    data : ResultData
        MIKE 1D ResultData object.
    data_items : IDataItems.
        MIKE 1D IDataItems object.
    quantity_label : str
        A label, which is appended if the quantity id starts
        with a number. The value used is quantity_label = 'q_'
    result_quantity_map : dict
        Dictionary from quantity id to a list of ResultQuantity objects.
    result_quantity_derived_map : dict
        Dictionary from derived quantity id to a ResultQuantityDerivedCollection object.
    """

    def __init__(self, res1d: Res1D):
        self.res1d = res1d
        self.quantity_label = "q_"
        self.data = res1d.data
        self.data_items = res1d.data.DataItems
        self.result_quantity_map: Dict[str : List[ResultQuantity]] = {}
        self.result_quantity_derived_map = {}
        self._group = None

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}>"

    def _repr_html_(self) -> str:
        total_names = len(self)
        total_quantities = len(self.quantities)
        pretty_quantities = [
            ResultQuantity.prettify_quantity(self.result_quantity_map[qid][0])
            for qid in self.result_quantity_map
        ]
        repr = build_html_repr_from_sections(
            self.__repr__(),
            [
                (f"Names ({total_names})", self.names),
                (f"Quantities ({total_quantities})", pretty_quantities),
            ],
        )
        return repr

    @property
    def group(self) -> TimeSeriesIdGroup:
        """The TimeSeriesIdGroup associated with these locations."""
        return self._group

    @property
    def quantities(self) -> Dict[str, ResultQuantityCollection]:
        """A list of available quantities."""
        return {k: getattr(self, k) for k in self.result_quantity_map}

    @property
    def derived_quantities(self) -> List[str]:
        """A list of available derived quantities."""
        return list(self.result_quantity_derived_map.keys())

    @property
    def names(self) -> List[str]:
        """A list of location names (e.g. MUIDs)."""
        return list(self.keys())

    @property
    def locations(self) -> List[ResultLocation]:
        """A list of location objects (e.g. <ResultNode>)."""
        return list(self.values())

    def read(
        self,
        column_mode: Optional[str | ColumnMode] = None,
        include_derived: bool = False,
    ) -> pd.DataFrame:
        """
        Read the time series data for all quantities at these locations into a DataFrame.

        Parameters
        ----------
        column_mode : str | ColumnMode (optional)
            Specifies the type of column index of returned DataFrame.
            'all' - column MultiIndex with levels matching TimeSeriesId objects.
            'compact' - same as 'all', but removes levels with default values.
            'timeseries' - column index of TimeSeriesId objects

        include_derived: bool, default False
            Include derived quantities.
        """
        result_quantities = [
            q for qlist in self.result_quantity_map.values() for q in qlist
        ]
        timesries_ids = [q.timeseries_id for q in result_quantities]

        if include_derived:
            column_mode = "compact"
        df = self.res1d.result_reader.read(timesries_ids, column_mode=column_mode)

        if include_derived:
            df_derived = []
            for dq in self.result_quantity_derived_map.values():
                df_derived.append(dq.read(column_mode=column_mode))
            df = pd.concat([df, *df_derived], axis=1)

        return df

    def set_quantity_collections(self):
        """Sets all quantity collection attributes."""
        for quantity_id in self.result_quantity_map:
            result_quantities = self.result_quantity_map[quantity_id]
            result_quantity_collection = ResultQuantityCollection(
                result_quantities, self.res1d
            )
            result_quantity_attribute_string = make_proper_variable_name(
                quantity_id, self.quantity_label
            )
            setattr(self, result_quantity_attribute_string, result_quantity_collection)

    def _can_add_derived_quantity(self, derived_quantity: DerivedQuantity) -> bool:
        """
        Check if a derived quantity can be added to the result locations."""
        if self.group not in derived_quantity.groups:
            return False
        elif derived_quantity.source_quantity not in self.result_quantity_map:
            return False
        return True

    def add_derived_quantity(self, derived_quantity: DerivedQuantity):
        """
        Add a derived quantity to the result network.

        Parameters
        ----------
        derived_quantity : DerivedQuantity
            Derived quantity to be added to the result network.
        """
        if self._can_add_derived_quantity(derived_quantity):
            self.set_quantity_derived(derived_quantity)

        for location in self.values():
            location.add_derived_quantity(derived_quantity)

    def remove_derived_quantity(self, derived_quantity: DerivedQuantity | str):
        """
        Remove a derived quantity from the result network.

        Parameters
        ----------
        derived_quantity : DerivedQuantity or str
            Derived quantity to be removed from the result network. Either a DerivedQuantity object or its name.
        """
        # remove from self.result_quantity_derived_map
        if isinstance(derived_quantity, DerivedQuantity):
            derived_quantity = derived_quantity.name

        self.result_quantity_derived_map.pop(derived_quantity, None)

        result_quantity_attribute_string = make_proper_variable_name(
            derived_quantity, self.quantity_label
        )
        if hasattr(self, result_quantity_attribute_string):
            delattr(self, result_quantity_attribute_string)

        for location in self.values():
            location.remove_derived_quantity(derived_quantity)

    def set_quantity_derived(self, derived_quantity: DerivedQuantity):
        """Sets a single derived quantity attribute on the obj."""
        result_quantity_derived = ResultQuantityDerivedCollection(
            derived_quantity, self, self.res1d
        )
        quantity_id = result_quantity_derived.name

        self.result_quantity_derived_map[result_quantity_derived.name] = (
            result_quantity_derived
        )

        result_quantity_attribute_string = make_proper_variable_name(
            quantity_id, self.quantity_label
        )
        setattr(self, result_quantity_attribute_string, result_quantity_derived)

    def set_res1d_object_to_dict(self, dict_key, obj):
        """
        Create a dict entry from a key name to an object
        or a list of objects.
        """
        obj = impl(obj)
        if dict_key in self:
            value = self[dict_key]
            if not isinstance(value, list):
                self[dict_key] = [value]

            self[dict_key].append(obj)
        else:
            self[dict_key] = obj
