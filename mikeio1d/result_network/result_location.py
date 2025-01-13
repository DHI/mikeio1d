"""ResultLocation class."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from typing import Dict
    from typing import List
    from typing import Optional
    import pandas as pd

    from ..res1d import Res1D
    from ..result_reader_writer.result_reader import ColumnMode
    from ..query import QueryData

    from DHI.Mike1D.ResultDataAccess import IRes1DDataSet
    from DHI.Mike1D.ResultDataAccess import IDataItem

from abc import ABC
from abc import abstractmethod

from ..quantities import TimeSeriesId
from ..quantities import TimeSeriesIdGroup
from ..quantities import DerivedQuantity

from .result_quantity import ResultQuantity
from .result_quantity_derived import ResultQuantityDerived
from .various import make_proper_variable_name
from .various import build_html_repr_from_sections


class ResultLocation(ABC):
    """A base class for a network location (node, reach) or a catchment wrapper class."""

    def __init__(self):
        self._group: TimeSeriesIdGroup = ""
        self._name: str = ""
        self._tag: str = ""
        self._creator: ResultLocationCreator = None

    def __repr__(self) -> str:
        """Return a string representation of the object."""
        return f"<{self.__class__.__name__}>"

    def _repr_html_(self) -> str:
        return self._creator.repr_html()

    @property
    def res1d(self) -> Res1D:
        """The Res1D instance that this location belongs to."""
        return self._creator.res1d

    @property
    def group(self) -> TimeSeriesIdGroup:
        """The TimeSeriesIdGroup assosciated with this location."""
        return self._group

    @property
    def quantities(self) -> List[str]:
        """A list of available quantities."""
        return list(self._creator.result_quantity_map.keys())

    @property
    def derived_quantities(self) -> List[str]:
        """A list of available derived quantities."""
        return list(self._creator.result_quantity_derived_map.keys())

    @abstractmethod
    def get_m1d_dataset(self, m1d_dataitem: IDataItem = None) -> IRes1DDataSet:
        """Get IRes1DDataSet object associated with ResultLocation.

        Parameters
        ----------
        m1d_dataitem: IDataItem
            Usually ignored, except for ResultReach.

        Returns
        -------
        IRes1DDataSet
            IRes1DDataSet object associated with ResultLocation.

        """
        ...

    @abstractmethod
    def get_query(self, data_item: IDataItem) -> QueryData:
        """Create a query for given data item."""
        ...

    def add_query(self, data_item: IDataItem):
        """Add a query to ResultNetwork.queries list."""
        query = self.get_query(data_item)
        self.res1d.network.add_query(query)

    def read(self, column_mode: Optional[str | ColumnMode] = None) -> pd.DataFrame:
        """Read the time series data for all quantities at this location into a DataFrame.

        Parameters
        ----------
        column_mode : str | ColumnMode (optional)
            Specifies the type of column index of returned DataFrame.
            'all' - column MultiIndex with levels matching TimeSeriesId objects.
            'compact' - same as 'all', but removes levels with default values.
            'timeseries' - column index of TimeSeriesId objects

        """
        qlists = self._creator.result_quantity_map.values()
        result_quantities = [q for qlist in qlists for q in qlist]
        timesries_ids = [q.timeseries_id for q in result_quantities]
        reader = self.res1d.reader
        df = reader.read(timesries_ids, column_mode=column_mode)
        return df


class ResultLocationCreator(ABC):
    """A base helper class for creating ResultLocation.

    Parameters
    ----------
    result_location: ResultLocation
        Instance of ResultLocation, which the ResultLocationCreator deals with.
    data_items: IDataItems
        MIKE 1D IDataItems object.
    res1d : Res1D
        Res1D object the result location belongs to.

    Attributes
    ----------
    quantity_label : str
        A label, which is appended if the quantity id starts
        with a number. The value used is quantity_label = 'q_'
    result_quantity_map : dict
        Dictionary from quantity id to a list of ResultQuantity objects.
        For ResultLocation this list contains a single element.
    result_quantity_map_derived : dict
        Dictionary from quantity id to a list of ResultQuantityDerived objects.
    element_indices : list
        List of integers representing element index for entries in data_items.
        For non grid point locations this is typically None.
    static_attributes : list
        List of static attributes, that is mainly used when generating HTML representation.

    """

    def __init__(
        self,
        result_location: ResultLocation,
        data_items: List[IDataItem],
        res1d: Res1D,
    ):
        self.result_location = result_location
        self.data_items = data_items
        self.res1d = res1d

        self.quantity_label = "q_"
        self.result_quantity_map: Dict[str, List[ResultQuantity]] = {}
        self.result_quantity_derived_map: Dict[str, ResultQuantityDerived] = {}
        self.element_indices: List[int] = None
        self.static_attributes: List[str] = []

    @abstractmethod
    def create(self):
        """Perform ResultLocation creation steps."""
        ...

    def repr_html(self) -> str:
        """HTML representation."""
        result_location = self.result_location
        attributes = {k: getattr(result_location, k) for k in self.static_attributes}
        total_attributes = len(attributes)
        total_quantities = len(result_location.quantities)
        total_derived_quantities = len(result_location.derived_quantities)
        pretty_quantities = [
            ResultQuantity.prettify_quantity(self.result_quantity_map[qid][0])
            for qid in self.result_quantity_map
        ]
        header = self.result_location.__repr__()
        sections = [
            (f"Attributes ({total_attributes})", attributes),
            (f"Quantities ({total_quantities})", pretty_quantities),
            (
                f"Derived Quantities ({total_derived_quantities})",
                result_location.derived_quantities,
            ),
        ]
        repr = build_html_repr_from_sections(header, sections)
        return repr

    def set_static_attribute(self, name: str):
        """Add static attribute. This shows up in the html repr."""
        self.static_attributes.append(name)

    def set_quantities(self):
        """Set all quantity attributes."""
        element_indices = self.element_indices
        data_items = list(self.data_items)
        data_items_count = len(data_items)
        for i in range(data_items_count):
            data_item = data_items[i]
            element_index = element_indices[i] if element_indices is not None else 0
            self.set_quantity(self.result_location, data_item, element_index)

    def set_quantity(
        self,
        obj: ResultLocation,
        data_item: IDataItem,
        element_index: int = 0,
    ):
        """Set a single quantity attribute on the obj."""
        if not self.res1d.filter.is_data_item_included(data_item):
            return

        m1d_dataset = self.result_location.get_m1d_dataset(data_item)
        result_quantity = ResultQuantity(obj, data_item, self.res1d, m1d_dataset, element_index)
        self.res1d.network._add_result_quantity_to_map(result_quantity)

        quantity = data_item.Quantity
        quantity_id = quantity.Id

        result_quantity_attribute_string = make_proper_variable_name(
            quantity_id, self.quantity_label
        )
        setattr(obj, result_quantity_attribute_string, result_quantity)

        self.add_to_result_quantity_maps(quantity_id, result_quantity)

    def can_add_derived_quantity(self, derived_quantity: DerivedQuantity) -> bool:
        """Check if a derived quantity can be added to the result locations."""
        result_location = self.result_location
        if result_location.group not in derived_quantity.groups:
            return False
        elif derived_quantity.source_quantity not in result_location.quantities:
            return False
        return True

    def add_derived_quantity(self, derived_quantity: DerivedQuantity):
        """Add a derived quantity to the result location."""
        if self.can_add_derived_quantity(derived_quantity):
            self.set_quantity_derived(derived_quantity)

    def remove_derived_quantity(self, derived_quantity: DerivedQuantity | str):
        """Remove a derived quantity from the result location."""
        if isinstance(derived_quantity, DerivedQuantity):
            derived_quantity = derived_quantity.name

        self.result_quantity_derived_map.pop(derived_quantity, None)

        result_quantity_attribute_string = make_proper_variable_name(
            derived_quantity, self.quantity_label
        )
        if hasattr(self.result_location, result_quantity_attribute_string):
            delattr(self.result_location, result_quantity_attribute_string)

    def set_quantity_derived(self, derived_quantity: DerivedQuantity):
        """Set a single derived quantity attribute on the obj."""
        result_quantity_derived = ResultQuantityDerived(
            derived_quantity, self.result_location, self.res1d
        )
        quantity_id = result_quantity_derived.name

        self.result_quantity_derived_map[result_quantity_derived.name] = result_quantity_derived

        result_quantity_attribute_string = make_proper_variable_name(
            quantity_id, self.quantity_label
        )
        setattr(self.result_location, result_quantity_attribute_string, result_quantity_derived)

    @abstractmethod
    def add_to_result_quantity_maps(self, quantity_id: str, result_quantity: ResultQuantity):
        """Add to result quantity maps.

        Result quantity map is a dictionary from quantity id to a list of result quantities corresponding to that quantity id.

        Parameters
        ----------
        quantity_id : str
            Quantity id.
        result_quantity : ResultQuantity
            One of the possible ResultQuantity objects corresponding to a quantity id.

        """
        ...

    def add_to_result_quantity_map(
        self,
        quantity_id: str,
        result_quantity: ResultQuantity,
        result_quantity_map: Dict[str, List[ResultQuantity]],
    ):
        """Add to a given result quantity map.

        Parameters
        ----------
        quantity_id : str
            Quantity id.
        result_quantity : ResultQuantity
            One of the possible ResultQuantity objects corresponding to a quantity id.
        result_quantity_map : dict
            Dictionary from quantity id to a list of ResultQuantity objects.

        """
        if quantity_id in result_quantity_map:
            result_quantity_map[quantity_id].append(result_quantity)
        else:
            result_quantity_map[quantity_id] = [result_quantity]

    def add_to_network_result_quantity_map(self, result_quantity: ResultQuantity) -> TimeSeriesId:
        """Add a ResultQuantity to map of all possible ResultQuantities.

        Parameters
        ----------
        result_quantity : ResultQuantity
            ResultQuantity object to be added to the result_quantity_map.

        Returns
        -------
        TimeSeriesId
            The TimeSeriesId key of the added ResultQuantity

        """
        network = self.res1d.network
        tsid = network._add_result_quantity_to_map(result_quantity)
        return tsid
