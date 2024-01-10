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
class TimeseriesId:
    """
    A unique identifier for a timeseries result on the Mike 1D network.
    """

    quantity: str
    """The name of the physical quantity (e.g. 'Discharge')"""
    group: str
    """Dataset group the timeseries is associated with. Can be all enumerations of ItemTypeGroup (e.g. NodeItem, ReachItem, etc.)"""
    name: str
    """The unique name of the network element where the timeseries exists."""
    chainage: str
    """Chainage of the GridPoint that this data is assosciated with (only relevant for groups of type reach)."""
    tag: str = ""
    """An additional tag used to further define uniqueness where needed."""
    duplicate: int = 0
    """A fallback to enumerate ids where duplicate timeseries are found."""
    derived: bool = False
    """Whether the timeseries is derived rather than saved in the result file."""

    def astuple(self) -> Tuple:
        """Converts a TimeseriesId to a tuple."""
        return dataclasses.astuple(self)

    def to_m1d(self, res1d: Res1D) -> DataEntry:
        """Converts a TimeseriesId to its assosciated Mike1D objects.

        Returns
        -------
        DataEntry
            A DataEntry object containing the assosciated Mike1D objects,
            or None if the TimeseriesId is derived.
        """
        if self.derived:
            raise ValueError("Cannot convert derived TimeseriesId to DataEntry")

        result_quantity = self.to_result_quantity(res1d)
        data_entry = result_quantity.get_data_entry()
        return data_entry

    def to_result_quantity(self, res1d: Res1D) -> ResultQuantity:
        """Converts a TimeseriesId to a ResultQuantity object.

        Returns
        -------
        ResultQuantity
            A ResultQuantity object containing the assosciated Mike1D objects,
            or None if the TimeseriesId is derived.
        """
        if self.derived:
            raise ValueError("Cannot convert derived TimeseriesId to ResultQuantity")

        quantity_map = res1d.result_network.result_quantity_map
        query = self.to_query()
        result_quantity = quantity_map.get(str(query), None)

        if result_quantity is None:
            raise ValueError(f"Could not convert TimeseriesId to ResultQuantity: {self}")

        return result_quantity

    def to_query(self) -> QueryData:
        """Converts a TimeseriesId to a QueryData object."""
        if self.derived:
            raise ValueError("Cannot convert derived TimeseriesId to QueryData")

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
        elif self.group == "StructureItem":
            from ..query import QueryDataStructure

            return QueryDataStructure(
                quantity=self.quantity,
                structure=self.name,
            )
        else:
            raise ValueError(f"No query exists for group: {self.group}")

    @staticmethod
    def from_tuple(t: Tuple) -> TimeseriesId:
        """Convert a tuple to a TimeseriesId object."""
        return TimeseriesId(
            quantity=t[0],
            group=t[1],
            name=t[2],
            chainage=t[3],
            tag=t[4],
            duplicate=t[5],
            derived=t[6],
        )

    @staticmethod
    def to_multiindex(timeseries_ids: List[TimeseriesId]) -> pd.MultiIndex:
        """Convert a list of TimeseriesId objects to a pandas MultiIndex."""
        return pd.MultiIndex.from_tuples(
            [dataclasses.astuple(tsid) for tsid in timeseries_ids],
            names=["quantity", "group", "name", "chainage", "tag", "duplicate", "derived"],
        )

    @staticmethod
    def from_multiindex(index: pd.MultiIndex) -> List[TimeseriesId]:
        """Convert a pandas MultiIndex to a list of TimeseriesId objects."""
        return [
            TimeseriesId(
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
    ) -> TimeseriesId:
        """Create a TimeseriesId object from an IRes1DDataSet, IRes1DDataItem and element index.

        Parameters
        ----------
        m1d_dataset : IRes1DDataSet
            The dataset to create a TimeseriesId for.
        m1d_dataitem : IRes1DDataItem
            The dataitem to create a TimeseriesId for.
        element_index : int
            The index of the element within the IRes1DDataItem."""

        quantity = m1d_dataitem.Quantity.Id
        group = m1d_dataitem.ItemTypeGroup.ToString()
        item_id = m1d_dataitem.ItemId
        name = TimeseriesId.get_dataset_name(m1d_dataset, item_id)

        chainage = None
        if m1d_dataitem.IndexList is not None:
            chainages = m1d_dataset.GetChainages(m1d_dataitem)
            chainage = chainages[element_index]

        tag = None

        return TimeseriesId(
            quantity=quantity,
            group=group,
            name=name,
            chainage=chainage,
            tag=tag,
        )

    @staticmethod
    def from_result_quantity(result_quantity: ResultQuantity) -> TimeseriesId:
        """Create a TimeseriesId object from a ResultQuantity object."""
        m1d_dataitem = result_quantity.data_item
        m1d_dataset = result_quantity.m1d_dataset
        element_index = result_quantity.element_index

        timeseries_id = TimeseriesId.from_dataset_dataitem_and_element(
            m1d_dataset, m1d_dataitem, element_index
        )

        return timeseries_id

    @staticmethod
    def get_dataset_name(m1d_dataset, item_id=None, delimiter=NAME_DELIMITER) -> str:
        """Create a unique name for a dataset.

        Used to create the 'name' field of TimeseriesId.

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
