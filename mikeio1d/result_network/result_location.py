from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from typing import Dict
    from typing import List
    from typing import Optional

    import pandas as pd

    from ..res1d import Res1D
    from ..result_reader_writer.result_reader import ColumnMode

from abc import ABC
from abc import abstractclassmethod

from .result_quantity import ResultQuantity
from .result_quantity_derived import ResultQuantityDerived
from .various import make_proper_variable_name
from .various import build_html_repr_from_sections
from ..quantities import TimeSeriesId
from ..quantities import DerivedQuantity


class ResultLocation(ABC):
    """
    A base class for a network location (node, reach)
    or a catchment wrapper class.

    Parameters
    ----------
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
    """

    def __init__(self, data_items, res1d: Res1D):
        self.data_items = data_items
        self.res1d = res1d
        self.quantity_label = "q_"
        self.result_quantity_map: Dict[str, List[ResultQuantity]] = {}
        self.result_quantity_derived_map: Dict[str, ResultQuantityDerived] = {}
        self.element_indices = None
        self._static_attributes = []

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}>"

    def _repr_html_(self) -> str:
        attributes = {k: getattr(self, k) for k in self._static_attributes}
        total_attributes = len(attributes)
        total_quantities = len(self.quantities)
        pretty_quantities = [
            ResultQuantity.prettify_quantity(self.result_quantity_map[qid][0])
            for qid in self.result_quantity_map
        ]
        repr = build_html_repr_from_sections(
            self.__repr__(),
            [
                (f"Attributes ({total_attributes})", attributes),
                (f"Quantities ({total_quantities})", pretty_quantities),
            ],
        )
        return repr

    def read(self, column_mode: Optional[str | ColumnMode] = None) -> pd.DataFrame:
        """
        Read the time series data for all quantities at this location into a DataFrame.

        Parameters
        ----------
        column_mode : str | ColumnMode (optional)
            Specifies the type of column index of returned DataFrame.
            'all' - column MultiIndex with levels matching TimeSeriesId objects.
            'compact' - same as 'all', but removes levels with default values.
            'timeseries' - column index of TimeSeriesId objects
        """
        result_quantities = [
            q for qlist in self.result_quantity_map.values() for q in qlist
        ]
        timesries_ids = [q.timeseries_id for q in result_quantities]
        df = self.res1d.result_reader.read(timesries_ids, column_mode=column_mode)
        return df

    @property
    def group(self) -> List[str]:
        """The TimeSeriesIdGroup assosciated with this location."""
        return self._group

    @property
    def quantities(self) -> List[str]:
        """A list of available quantities."""
        return list(self.result_quantity_map.keys())

    @property
    def derived_quantities(self) -> List[str]:
        """A list of available derived quantities."""
        return list(self.result_quantity_derived_map.keys())

    def set_static_attribute(self, key, value):
        """Add static attribute. This shows up in the html repr"""
        self._static_attributes.append(key)
        setattr(self, key, value)

    def set_quantities(self):
        """Sets all quantity attributes."""
        element_indices = self.element_indices
        data_items = list(self.data_items)
        data_items_count = len(data_items)
        for i in range(data_items_count):
            data_item = data_items[i]
            element_index = element_indices[i] if element_indices is not None else 0
            self.set_quantity(self, data_item, element_index)

    def set_quantity(self, obj, data_item, element_index=0):
        """Sets a single quantity attribute on the obj."""
        m1d_dataset = self.get_m1d_dataset(data_item)
        result_quantity = ResultQuantity(
            obj, data_item, self.res1d, m1d_dataset, element_index
        )
        self.res1d.result_network.add_result_quantity_to_map(result_quantity)

        quantity = data_item.Quantity
        quantity_id = quantity.Id

        result_quantity_attribute_string = make_proper_variable_name(
            quantity_id, self.quantity_label
        )
        setattr(obj, result_quantity_attribute_string, result_quantity)

        self.add_to_result_quantity_maps(quantity_id, result_quantity)

    def _can_add_derived_quantity(self, derived_quantity: DerivedQuantity) -> bool:
        """
        Check if a derived quantity can be added to the result locations."""
        if self.group not in derived_quantity.groups:
            return False
        elif derived_quantity.source_quantity not in self.quantities:
            return False
        return True

    def add_derived_quantity(self, derived_quantity: DerivedQuantity):
        """Add a derived quantity to the result location."""
        if self._can_add_derived_quantity(derived_quantity):
            self.set_quantity_derived(derived_quantity)

    def remove_derived_quantity(self, derived_quantity: DerivedQuantity | str):
        if isinstance(derived_quantity, DerivedQuantity):
            derived_quantity = derived_quantity.name

        self.result_quantity_derived_map.pop(derived_quantity, None)

        result_quantity_attribute_string = make_proper_variable_name(
            derived_quantity, self.quantity_label
        )
        if hasattr(self, result_quantity_attribute_string):
            delattr(self, result_quantity_attribute_string)

    def set_quantity_derived(self, derived_quantity: DerivedQuantity):
        """Sets a single derived quantity attribute on the obj."""
        result_quantity_derived = ResultQuantityDerived(
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

    @abstractclassmethod
    def get_m1d_dataset(self, m1d_dataitem=None):
        """Base method for getting IRes1DDataSet object associated with ResultLocation.

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

    @abstractclassmethod
    def add_to_result_quantity_maps(
        self, quantity_id: str, result_quantity: ResultQuantity
    ):
        """
        Base method for adding to result quantity maps, which is a dictionary
        from quantity id to a list of result quantities corresponding to that
        quantity id.

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
        """
        Method for adding to a given result quantity map.

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

    def add_to_network_result_quantity_map(
        self, result_quantity: ResultQuantity
    ) -> TimeSeriesId:
        """
        Add a ResultQuantity to map of all possible ResultQuantities.

        Parameters
        ----------
        result_quantity : ResultQuantity
            ResultQuantity object to be added to the result_quantity_map.

        Returns
        -------
        TimeSeriesId
            The TimeSeriesId key of the added ResultQuantity
        """
        network = self.res1d.result_network
        tsid = network.add_result_quantity_to_map(result_quantity)
        return tsid

    def add_query(self, data_item):
        """Base method for adding a query to ResultNetwork.queries list."""
        query = self.get_query(data_item)
        self.res1d.result_network.add_query(query)

    @abstractclassmethod
    def get_query(self, data_item):
        """Base method for creating a query for given data item."""
        ...
