from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import List
    from ..result_network.result_quantity import ResultQuantity

import dataclasses
from dataclasses import dataclass
import pandas as pd

from ..various import NAME_DELIMITER


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

    @staticmethod
    def to_multiindex(timeseries_ids: List[TimeseriesId]) -> pd.MultiIndex:
        """Convert a list of TimeseriesId objects to a pandas MultiIndex"""
        return pd.MultiIndex.from_tuples(
            [dataclasses.astuple(tsid) for tsid in timeseries_ids],
            names=["quantity", "group", "name", "chainage", "tag", "duplicate", "derived"],
        )

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
