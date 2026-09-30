"""ResultLocation class."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from pathlib import Path

    import pandas as pd
    from matplotlib.axes import Axes

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
    def quantities(self) -> list[str]:
        """A list of available quantities."""
        return list(self._creator.result_quantity_map.keys())

    @property
    def derived_quantities(self) -> list[str]:
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

    def add(self, quantities: str | list[str] | None = None) -> None:
        """Add quantities at this location to ResultNetwork.queue for reading later.

        Parameters
        ----------
        quantities : str | list[str] | None
            Quantity id or list of quantity ids to add. If None, all quantities are added.

        """
        for result_quantity in self._get_result_quantities(quantities):
            result_quantity.add()

    def read(
        self,
        column_mode: str | ColumnMode | None = None,
        quantities: str | list[str] | None = None,
    ) -> pd.DataFrame:
        """Read the time series data for quantities at this location into a DataFrame.

        Parameters
        ----------
        column_mode : str | ColumnMode (optional)
            Specifies the type of column index of returned DataFrame.
            'all' - column MultiIndex with levels matching TimeSeriesId objects.
            'compact' - same as 'all', but removes levels with default values.
            'timeseries' - column index of TimeSeriesId objects
        quantities : str | list[str] | None
            Quantity id or list of quantity ids to read. If None, all quantities are read.

        Returns
        -------
        pd.DataFrame
            Time series data with one column per time series.

        Raises
        ------
        ValueError
            If a quantity is not available at this location.

        """
        timeseries_ids = self._get_timeseries_ids(quantities)
        return self.res1d.reader.read(timeseries_ids, column_mode=column_mode)

    def to_dataframe(
        self,
        column_mode: str | ColumnMode | None = None,
        quantities: str | list[str] | None = None,
    ) -> pd.DataFrame:
        """Read the time series data for quantities at this location into a DataFrame.

        Alias for read() method.

        Parameters
        ----------
        column_mode : str | ColumnMode (optional)
            Specifies the type of column index of returned DataFrame.
            'all' - column MultiIndex with levels matching TimeSeriesId objects.
            'compact' - same as 'all', but removes levels with default values.
            'timeseries' - column index of TimeSeriesId objects
        quantities : str | list[str] | None
            Quantity id or list of quantity ids to read. If None, all quantities are read.

        Returns
        -------
        pd.DataFrame
            Time series data with one column per time series.

        """
        return self.read(column_mode, quantities)

    def plot(
        self,
        ax: Axes | None = None,
        quantities: str | list[str] | None = None,
        **kwargs,
    ) -> Axes:
        """Plot the time series data for quantities at this location.

        Parameters
        ----------
        ax : matplotlib.axes.Axes, optional
            Axes object to plot on.
        quantities : str | list[str] | None
            Quantity id or list of quantity ids to plot. If None, all quantities are plotted.
        **kwargs
            Additional keyword arguments passed to pandas.DataFrame.plot.

        Returns
        -------
        matplotlib.axes.Axes
            Axes object with the plot.

        """
        result_quantities = self._get_result_quantities(quantities)
        timeseries_ids = [q.timeseries_id for q in result_quantities]
        df = self.res1d.reader.read(timeseries_ids)
        ax = df.plot(ax=ax, **kwargs)
        ax.set_xlabel("Time")
        if len({q.name for q in result_quantities}) == 1:
            ylabel = ResultQuantity.prettify_quantity(result_quantities[0], latex_format=True)
            ax.set_ylabel(ylabel)
        else:
            ax.set_ylabel("")
        ax.grid(True)
        return ax

    def to_csv(
        self,
        file_path: str | Path,
        time_step_skipping_number: int = 1,
        quantities: str | list[str] | None = None,
    ) -> None:
        """Extract time series data for quantities at this location into a csv file.

        Parameters
        ----------
        file_path : str | Path
            Output file path.
        time_step_skipping_number : int, default=1
            Number specifying the time step frequency to output.
        quantities : str | list[str] | None
            Quantity id or list of quantity ids to extract. If None, all quantities are extracted.

        """
        timeseries_ids = self._get_timeseries_ids(quantities)
        self.res1d.to_csv(file_path, timeseries_ids, time_step_skipping_number)

    def to_dfs0(
        self,
        file_path: str | Path,
        time_step_skipping_number: int = 1,
        quantities: str | list[str] | None = None,
    ) -> None:
        """Extract time series data for quantities at this location into a dfs0 file.

        Parameters
        ----------
        file_path : str | Path
            Output file path.
        time_step_skipping_number : int, default=1
            Number specifying the time step frequency to output.
        quantities : str | list[str] | None
            Quantity id or list of quantity ids to extract. If None, all quantities are extracted.

        """
        timeseries_ids = self._get_timeseries_ids(quantities)
        self.res1d.to_dfs0(file_path, timeseries_ids, time_step_skipping_number)

    def to_txt(
        self,
        file_path: str | Path,
        time_step_skipping_number: int = 1,
        quantities: str | list[str] | None = None,
    ) -> None:
        """Extract time series data for quantities at this location into a txt file.

        Parameters
        ----------
        file_path : str | Path
            Output file path.
        time_step_skipping_number : int, default=1
            Number specifying the time step frequency to output.
        quantities : str | list[str] | None
            Quantity id or list of quantity ids to extract. If None, all quantities are extracted.

        """
        timeseries_ids = self._get_timeseries_ids(quantities)
        self.res1d.to_txt(file_path, timeseries_ids, time_step_skipping_number)

    def _get_timeseries_ids(self, quantities: str | list[str] | None = None) -> list[TimeSeriesId]:
        return [q.timeseries_id for q in self._get_result_quantities(quantities)]

    def _get_result_quantities(
        self, quantities: str | list[str] | None = None
    ) -> list[ResultQuantity]:
        """Get the ResultQuantity objects at this location for the given quantity ids.

        Returns
        -------
        list[ResultQuantity]
            The ResultQuantity objects, in the order the quantity ids were given. A quantity id
            given more than once is only included once.

        Raises
        ------
        ValueError
            If a quantity id is unknown, rather than returning an empty list, because the
            readers and extractors treat an empty list as 'read everything queued'.

        """
        result_quantity_map = self._creator.result_quantity_map
        if quantities is None:
            if len(result_quantity_map) == 0:
                raise ValueError(f"{self!r} has no quantities.")
            quantities = list(result_quantity_map)
        elif isinstance(quantities, str):
            quantities = [quantities]

        if len(quantities) == 0:
            raise ValueError("At least one quantity must be given.")

        quantities = list(dict.fromkeys(quantities))

        unknown = [q for q in quantities if q not in result_quantity_map]
        if unknown:
            raise ValueError(
                f"Quantities {unknown} not found for {self!r}. Available quantities: "
                f"{list(result_quantity_map)}"
            )

        return [rq for q in quantities for rq in result_quantity_map[q]]


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
        data_items: list[IDataItem],
        res1d: Res1D,
    ):
        self.result_location = result_location
        self.data_items = data_items
        self.res1d = res1d

        self.quantity_label = "q_"
        self.result_quantity_map: dict[str, list[ResultQuantity]] = {}
        self.result_quantity_derived_map: dict[str, ResultQuantityDerived] = {}
        self.element_indices: list[int] = None
        self.static_attributes: list[str] = []

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
        return (
            result_location.group in derived_quantity.groups
            and derived_quantity.source_quantity in result_location.quantities
        )

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
        result_quantity_map: dict[str, list[ResultQuantity]],
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
