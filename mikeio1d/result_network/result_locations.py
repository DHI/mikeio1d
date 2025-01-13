"""ResultLocations class."""

from __future__ import annotations

from typing import TYPE_CHECKING

from typing import Dict

if TYPE_CHECKING:  # pragma: no cover
    from typing import List
    from typing import Optional
    import pandas as pd

    from ..res1d import Res1D
    from ..result_reader_writer.result_reader import ColumnMode
    from ..quantities import TimeSeriesIdGroup

    from .result_location import ResultLocation
    from .result_quantity import ResultQuantity
    from .result_quantity_derived import ResultQuantityDerived

    from DHI.Mike1D.ResultDataAccess import ResultData
    from DHI.Mike1D.ResultDataAccess import IDataItems

from abc import ABC
from abc import abstractmethod
import pandas as pd

from ..dotnet import pythonnet_implementation as impl
from ..quantities import DerivedQuantity

from .result_location import ResultLocation
from .result_quantity import ResultQuantity
from .result_quantity_collection import ResultQuantityCollection
from .result_quantity_derived_collection import ResultQuantityDerivedCollection
from .various import make_proper_variable_name
from .various import build_html_repr_from_sections


class ResultLocations(ABC, Dict[str, ResultLocation]):
    """A base class for a network locations (nodes, reaches) or a catchments wrapper class."""

    def __init__(self):
        self._group = None
        self._creator: ResultLocationsCreator = None

    def __repr__(self) -> str:
        """Return a string representation of the object."""
        return f"<{self.__class__.__name__}> ({len(self)})"

    def _repr_html_(self) -> str:
        return self._creator.repr_html()

    @property
    def res1d(self) -> Res1D:
        """The Res1D instance that these locations belong to."""
        return self._creator.res1d

    @property
    def group(self) -> TimeSeriesIdGroup:
        """The TimeSeriesIdGroup associated with these locations."""
        return self._group

    @property
    def quantities(self) -> Dict[str, ResultQuantityCollection]:
        """A list of available quantities."""
        result_quantity_map = self._creator.result_quantity_map
        return {k: getattr(self, make_proper_variable_name(k)) for k in result_quantity_map}

    @property
    def derived_quantities(self) -> List[str]:
        """A list of available derived quantities."""
        return list(self._creator.result_quantity_derived_map.keys())

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
        """Read the time series data for all quantities at these locations into a DataFrame.

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
        qlists = self._creator.result_quantity_map.values()
        result_quantities = [q for qlist in qlists for q in qlist]
        timesries_ids = [q.timeseries_id for q in result_quantities]

        if include_derived:
            column_mode = "compact"

        reader = self.res1d.reader
        df = reader.read(timesries_ids, column_mode=column_mode)

        if include_derived:
            df_derived = []
            dqs = self._creator.result_quantity_derived_map.values()
            for dq in dqs:
                df_derived.append(dq.read(column_mode=column_mode))
            df = pd.concat([df, *df_derived], axis=1)

        return df


class ResultLocationsCreator(ABC):
    """A base helper class for creating ResultLocations.

    Parameters
    ----------
    result_locations: ResultLocations
        Instance of ResultLocations, which the ResultLocationsCreator deals with.
    res1d : Res1D
        Res1D object the result locations belongs to.

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

    def __init__(self, result_locations: ResultLocations, res1d: Res1D):
        self.result_locations = result_locations
        self.res1d = res1d

        self.quantity_label = "q_"
        self.data: ResultData = res1d.result_data
        self.data_items: IDataItems = res1d.result_data.DataItems
        self.result_quantity_map: Dict[str : List[ResultQuantity]] = {}
        self.result_quantity_derived_map: Dict[str, List[ResultQuantityDerived]] = {}

    @abstractmethod
    def create(self):
        """Perform ResultLocations creation steps."""
        ...

    def repr_html(self) -> str:
        """HTML representation."""
        locations = self.result_locations
        total_quantities = len(locations.quantities)
        total_derived_quantities = len(locations.derived_quantities)
        pretty_quantities = [
            ResultQuantity.prettify_quantity(self.result_quantity_map[qid][0])
            for qid in self.result_quantity_map
        ]
        header = locations.__repr__()
        sections = [
            (f"Quantities ({total_quantities})", pretty_quantities),
            (f"Derived Quantities ({total_derived_quantities})", locations.derived_quantities),
        ]
        repr = build_html_repr_from_sections(header, sections)
        return repr

    def set_quantity_collections(self, result_locations: ResultLocations = None):
        """Set all quantity collection attributes."""
        result_locations = self.result_locations if result_locations is None else result_locations

        for quantity_id in self.result_quantity_map:
            result_quantities = self.result_quantity_map[quantity_id]
            result_quantity_collection = ResultQuantityCollection(result_quantities, self.res1d)
            result_quantity_attribute_string = make_proper_variable_name(
                quantity_id, self.quantity_label
            )
            setattr(result_locations, result_quantity_attribute_string, result_quantity_collection)

    def can_add_derived_quantity(self, derived_quantity: DerivedQuantity) -> bool:
        """Check if a derived quantity can be added to the result locations."""
        if self.result_locations.group not in derived_quantity.groups:
            return False
        elif derived_quantity.source_quantity not in self.result_quantity_map:
            return False
        return True

    def add_derived_quantity(self, derived_quantity: DerivedQuantity):
        """Add a derived quantity to the result network.

        Parameters
        ----------
        derived_quantity : DerivedQuantity
            Derived quantity to be added to the result network.

        """
        if self.can_add_derived_quantity(derived_quantity):
            self.set_quantity_derived(derived_quantity)

        for location in self.result_locations.values():
            location._creator.add_derived_quantity(derived_quantity)

    def remove_derived_quantity(self, derived_quantity: DerivedQuantity | str):
        """Remove a derived quantity from the result network.

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

        for location in self.result_locations.values():
            location._creator.remove_derived_quantity(derived_quantity)

    def set_quantity_derived(self, derived_quantity: DerivedQuantity):
        """Set a single derived quantity attribute on the obj."""
        result_quantity_derived = ResultQuantityDerivedCollection(
            derived_quantity, self.result_locations, self.res1d
        )
        quantity_id = result_quantity_derived.name

        self.result_quantity_derived_map[result_quantity_derived.name] = result_quantity_derived

        result_quantity_attribute_string = make_proper_variable_name(
            quantity_id, self.quantity_label
        )
        setattr(self.result_locations, result_quantity_attribute_string, result_quantity_derived)

    def set_res1d_object_to_dict(self, dict_key: str, obj):
        """Create a dict entry from a key name to an object or a list of objects."""
        obj = impl(obj)
        result_locations = self.result_locations
        if dict_key in result_locations:
            value = result_locations[dict_key]
            if not isinstance(value, list):
                result_locations[dict_key] = [value]

            result_locations[dict_key].append(obj)
        else:
            result_locations[dict_key] = obj
