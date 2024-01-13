from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import List
    from typing import Tuple
    from ..res1d import Res1D
    from ..result_network.result_quantity import ResultQuantity
    from ..query import QueryData

import dataclasses
from dataclasses import dataclass
import pandas as pd

from ..various import NAME_DELIMITER
from ..result_network.data_entry import DataEntry


@dataclass(frozen=True)
class TimeSeriesId:
    """
    A unique identifier for a timeseries result on the Mike 1D network.
    """

    quantity: str = ""
    """The name of the physical quantity (e.g. 'Discharge')"""
    group: str = ""
    """Dataset group the timeseries is associated with. Can be all enumerations of ItemTypeGroup (e.g. NodeItem, ReachItem, etc.)"""
    name: str = ""
    """The unique name of the network element where the timeseries exists."""
    chainage: float = float("nan")
    """Chainage of the GridPoint that this data is assosciated with (only relevant for groups of type reach)."""
    tag: str = ""
    """An additional tag used to further define uniqueness where needed."""
    duplicate: int = 0
    """A fallback to enumerate ids where duplicate timeseries are found."""
    derived: bool = False
    """Whether the timeseries is derived rather than saved in the result file."""

    def __eq__(self, other: TimeSeriesId) -> bool:
        """Checks equality between two TimeSeriesId objects."""
        if other is self:
            return True
        if not isinstance(other, TimeSeriesId):
            return False

        # Note: nan != nan, so we need to check for this case
        if self.chainage != other.chainage and not (
            self.chainage != self.chainage and other.chainage != other.chainage
        ):
            return False

        return (
            self.quantity == other.quantity
            and self.group == other.group
            and self.name == other.name
            and self.tag == other.tag
            and self.duplicate == other.duplicate
            and self.derived == other.derived
        )

    def __hash__(self) -> int:
        """Hashes a TimeSeriesId object."""
        # Uses the hash of the string representation to handle nan values in chainage.
        return hash(str(self))

    def is_valid(self, res1d: Res1D) -> bool:
        """Checks whether a TimeSeriesId is valid for a given Res1D object.

        A TimeSeriesId is valid if it exists in the global result quantity map.

        Parameters
        ----------
        res1d : Res1D
            The Res1D object to check if the TimeSeriesId exists in.

        Returns
        -------
        bool
            True if the TimeSeriesId is valid, False otherwise.
        """
        quantity_map = res1d.result_network.result_quantity_map
        result_quantity = quantity_map.get(self, None)
        return result_quantity is not None

    def astuple(self) -> Tuple:
        """Converts a TimeSeriesId to a tuple."""
        return dataclasses.astuple(self)

    def to_m1d(self, res1d: Res1D) -> DataEntry:
        """Converts a TimeSeriesId to its assosciated Mike1D objects.

        Returns
        -------
        DataEntry
            A DataEntry object containing the assosciated Mike1D objects,
            or None if the TimeSeriesId is derived.
        """
        if self.derived:
            raise ValueError("Cannot convert derived TimeSeriesId to DataEntry")

        result_quantity = self.to_result_quantity(res1d)
        data_entry = result_quantity.get_data_entry()
        return data_entry

    def to_result_quantity(self, res1d: Res1D) -> ResultQuantity:
        """Converts a TimeSeriesId to a ResultQuantity object.

        Returns
        -------
        ResultQuantity
            A ResultQuantity object containing the assosciated Mike1D objects,
            or None if the TimeSeriesId is derived.
        """
        if self.derived:
            raise ValueError("Cannot convert derived TimeSeriesId to ResultQuantity")

        quantity_map = res1d.result_network.result_quantity_map
        result_quantity = quantity_map.get(self, None)

        if result_quantity is None:
            raise ValueError(f"Could not convert TimeSeriesId to ResultQuantity: {self}")

        return result_quantity

    def to_query(self) -> QueryData:
        """Converts a TimeSeriesId to a QueryData object."""
        if self.derived:
            raise ValueError("Cannot convert derived TimeSeriesId to QueryData")

        # Note: imports are here to avoid circular imports
        if self.group == "GlobalItem":
            from ..query import QueryDataGlobal

            return QueryDataGlobal.from_timeseries_id(self)
        elif self.group == "NodeItem":
            from ..query import QueryDataNode

            return QueryDataNode.from_timeseries_id(self)

        elif self.group == "ReachItem":
            from ..query import QueryDataReach

            return QueryDataReach.from_timeseries_id(self)
        elif self.group == "CatchmentItem":
            from ..query import QueryDataCatchment

            return QueryDataCatchment.from_timeseries_id(self)
        elif self.group == "ReachStructureItem":
            from ..query import QueryDataStructure

            return QueryDataStructure(
                quantity=self.quantity,
                structure=self.name,
            )
        else:
            raise ValueError(f"No query exists for group: {self.group}")

    def next_duplicate(self) -> TimeSeriesId:
        """Creates a duplicate TimeSeriesId object.

        Returns
        -------
        TimeSeriesId
            A TimeSeriesId object with the same fields as the original,
            except with duplicate incremented by 1.
        """
        return TimeSeriesId(
            quantity=self.quantity,
            group=self.group,
            name=self.name,
            chainage=self.chainage,
            tag=self.tag,
            duplicate=self.duplicate + 1,
            derived=self.derived,
        )

    def prev_duplicate(self) -> TimeSeriesId:
        """Creates a duplicate TimeSeriesId object.

        Returns
        -------
        TimeSeriesId
            A TimeSeriesId object with the same fields as the original,
            except with duplicate decremented by 1.
        """
        if self.duplicate == 0:
            raise ValueError("Cannot decrement duplicate below 0")
        return TimeSeriesId(
            quantity=self.quantity,
            group=self.group,
            name=self.name,
            chainage=self.chainage,
            tag=self.tag,
            duplicate=self.duplicate - 1,
            derived=self.derived,
        )

    @staticmethod
    def from_query(query: QueryData) -> TimeSeriesId:
        """Converts a QueryData object to a TimeSeriesId object."""
        return query.to_timeseries_id()

    @staticmethod
    def from_tuple(t: Tuple) -> TimeSeriesId:
        """Convert a tuple to a TimeSeriesId object."""
        return TimeSeriesId(
            quantity=t[0],
            group=t[1],
            name=t[2],
            chainage=t[3],
            tag=t[4],
            duplicate=t[5],
            derived=t[6],
        )

    @staticmethod
    def to_multiindex(timeseries_ids: List[TimeSeriesId]) -> pd.MultiIndex:
        """Convert a list of TimeSeriesId objects to a pandas MultiIndex."""
        return pd.MultiIndex.from_tuples(
            [tsid.astuple() for tsid in timeseries_ids],
            names=["quantity", "group", "name", "chainage", "tag", "duplicate", "derived"],
        )

    @staticmethod
    def from_multiindex(index: pd.MultiIndex) -> List[TimeSeriesId]:
        """Convert a pandas MultiIndex to a list of TimeSeriesId objects."""
        return [
            TimeSeriesId(
                quantity=quantity,
                group=group,
                name=name,
                chainage=chainage,
                tag=tag,
                duplicate=duplicate,
                derived=derived,
            )
            for quantity, group, name, chainage, tag, duplicate, derived in index
        ]

    @staticmethod
    def from_dataset_dataitem_and_element(
        m1d_dataset, m1d_dataitem, element_index: int
    ) -> TimeSeriesId:
        """Create a TimeSeriesId object from an IRes1DDataSet, IRes1DDataItem and element index.

        Parameters
        ----------
        m1d_dataset : IRes1DDataSet
            The dataset to create a TimeSeriesId for.
        m1d_dataitem : IRes1DDataItem
            The dataitem to create a TimeSeriesId for.
        element_index : int
            The index of the element within the IRes1DDataItem."""

        quantity = m1d_dataitem.Quantity.Id
        group = m1d_dataitem.ItemTypeGroup.ToString()
        item_id = m1d_dataitem.ItemId
        name = TimeSeriesId.get_dataset_name(m1d_dataset, item_id)

        chainage = float("nan")
        if m1d_dataitem.IndexList is not None:
            chainages = m1d_dataset.GetChainages(m1d_dataitem)
            chainage = chainages[element_index]

        # DataItem objects on this DataSet have an ItemTypeGroup set to GlobalItem
        if "DHI.Mike1D.ResultDataAccess.Epanet.Res1DTypedReach" in repr(m1d_dataset.__class__):
            group = "ReachItem"

        return TimeSeriesId(
            quantity=quantity,
            group=group,
            name=name,
            chainage=chainage,
        )

    @staticmethod
    def from_result_quantity(result_quantity: ResultQuantity) -> TimeSeriesId:
        """Create a TimeSeriesId object from a ResultQuantity object.

        Note: this method assumes there are no duplicates (e.g. duplicate = 0). To get the
        unique TimeSeriesId of a ResultQuantity, access its timeseries_id property.
        """
        m1d_dataitem = result_quantity.data_item
        m1d_dataset = result_quantity.m1d_dataset
        element_index = result_quantity.element_index

        timeseries_id = TimeSeriesId.from_dataset_dataitem_and_element(
            m1d_dataset, m1d_dataitem, element_index
        )

        return timeseries_id

    @staticmethod
    def get_dataset_name(m1d_dataset, item_id=None, delimiter=NAME_DELIMITER) -> str:
        """Create a unique name for a dataset.

        Used to create the 'name' field of TimeSeriesId.

        Parameters
        ----------
        m1d_dataset : IRes1DDataSet
            The dataset to create a name for.
        item_id : str, optional
            The item id to prepend to the name, by default None
        delimiter : str, optional
            The delimiter to use between the item id and the name"""

        name = None

        if hasattr(m1d_dataset, "Name"):
            name = m1d_dataset.Name
        elif hasattr(m1d_dataset, "Id"):
            name = m1d_dataset.Id
        elif m1d_dataset.Quantity is not None:
            name = m1d_dataset.Quantity.Id

        name = "" if name is None else name

        # Add item id if present before the name.
        # Needed for unique identification of structures.
        name = delimiter.join([item_id, name]) if item_id is not None else name

        return name
