"""TimeSeriesId class."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from typing import Any
    from typing import Optional
    from typing import List
    from typing import Tuple
    from ..res1d import Res1D
    from ..result_network.result_quantity import ResultQuantity
    from ..query import QueryData
    from ..result_network.data_entry import DataEntry
    from ..result_network import ResultLocation

import dataclasses
from dataclasses import dataclass
from dataclasses import fields

from enum import Enum
import pandas as pd

from ..various import NAME_DELIMITER
from ..various import DELETE_VALUE

from DHI.Mike1D.ResultDataAccess import ItemTypeGroup


class TimeSeriesIdGroup(str, Enum):
    """Enumeration of all possible groups for a TimeSeriesId."""

    GLOBAL = "Global"
    NODE = "Node"
    REACH = "Reach"
    CATCHMENT = "Catchment"
    STRUCTURE = "Structure"

    def __hash__(self) -> int:
        """Hashes a TimeSeriesIdGroup object."""
        return self.value.__hash__()

    def __repr__(self) -> str:
        """Representation of a TimeSeriesIdGroup object."""
        return self.value.__repr__()

    def __str__(self) -> str:
        """Return string representation of a TimeSeriesIdGroup object."""
        return self.value.__str__()

    @staticmethod
    def from_m1d_data_item(m1d_data_item) -> str:
        """Get the group of a TimeSeriesId from an IRes1DDataItem object."""
        m1d_group = m1d_data_item.ItemTypeGroup
        if m1d_group == ItemTypeGroup.GlobalItem:
            return TimeSeriesIdGroup.GLOBAL.value
        elif m1d_group == ItemTypeGroup.NodeItem:
            return TimeSeriesIdGroup.NODE.value
        elif m1d_group == ItemTypeGroup.ReachItem:
            # assume that if ItemId is not empty, it's a structure
            if m1d_data_item.ItemId:
                return TimeSeriesIdGroup.STRUCTURE.value
            else:
                return TimeSeriesIdGroup.REACH.value
        elif m1d_group == ItemTypeGroup.CatchmentItem:
            return TimeSeriesIdGroup.CATCHMENT.value
        elif m1d_group == ItemTypeGroup.ReachStructureItem:
            return TimeSeriesIdGroup.STRUCTURE.value
        else:
            raise ValueError(f"Unknown group: {m1d_data_item.ItemTypeGroup.ToString()}")


@dataclass(frozen=True)
class TimeSeriesId:
    """A unique identifier for a timeseries result on the Mike 1D network."""

    quantity: str = ""
    """The name of the physical quantity (e.g. 'Discharge')"""
    group: str | TimeSeriesIdGroup = ""
    """Dataset group the timeseries is associated with. Can be all enumerations of TimeSeriesIdGroup (e.g. 'Node', 'Reach', etc.)"""
    name: str = ""
    """The unique name of the network element where the timeseries exists."""
    chainage: float = float("nan")
    """Chainage of the GridPoint that this data is assosciated with (only relevant for groups of type reach)."""
    tag: str = ""
    """An additional tag used to further define uniqueness where needed (e.g. river that structure exists on)."""
    duplicate: int = 0
    """A fallback to enumerate ids where duplicate timeseries are found."""
    derived: bool = False
    """Whether the timeseries is derived rather than saved in the result file."""

    def __post_init__(self):
        """Post initialization validation of TimeSeriesId object."""
        self._validate_group()
        self._validate_chainage()

    def _validate_chainage(self):
        if self.chainage is None:
            raise ValueError("chainage cannot be None: use float('nan') instead")
        elif self.chainage == "":
            raise ValueError("chainage cannot be empty: use float('nan') instead")
        try:
            float(self.chainage)
        except ValueError:
            raise ValueError("chainage must be a float or an object that can be cast to a float")

    def _validate_group(self):
        if self.group in set(TimeSeriesIdGroup):
            return
        raise ValueError(f"Invalid group for TimeSeriesId: {self.group}")

    def __eq__(self, other: TimeSeriesId) -> bool:
        """Check equality between two TimeSeriesId objects."""
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
        """Check whether a TimeSeriesId is valid for a given Res1D object.

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
        quantity_map = res1d.network.result_quantity_map
        result_quantity = quantity_map.get(self, None)
        return result_quantity is not None

    def astuple(self) -> Tuple:
        """Convert a TimeSeriesId to a tuple."""
        return dataclasses.astuple(self)

    def to_data_entry(self, res1d: Res1D) -> DataEntry:
        """Convert a TimeSeriesId to its assosciated Mike1D objects.

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
        """Convert a TimeSeriesId to a ResultQuantity object.

        Returns
        -------
        ResultQuantity
            A ResultQuantity object containing the assosciated Mike1D objects,
            or None if the TimeSeriesId is derived.

        """
        if self.derived:
            raise ValueError("Cannot convert derived TimeSeriesId to ResultQuantity")

        quantity_map = res1d.network.result_quantity_map
        result_quantity = quantity_map.get(self, None)

        if result_quantity is None:
            raise ValueError(f"Could not convert TimeSeriesId to ResultQuantity: {self}")

        return result_quantity

    def get_location(self, res1d: Res1D) -> ResultLocation:
        """Get the ResultLocation associated with the TimeSeriesId.

        Returns
        -------
        ResultLocation
            The ResultLocation associated with the TimeSeriesId (e.g. ResultNode, ResultReach, etc.)

        """
        if self.derived:
            raise NotImplementedError("Cannot convert derived TimeSeriesId to ResultLocation")

        result_quantity = self.to_result_quantity(res1d)
        location = result_quantity.result_location
        return location

    def next_duplicate(self) -> TimeSeriesId:
        """Create a duplicate TimeSeriesId object.

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
        """Create a duplicate TimeSeriesId object.

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
        """Convert a QueryData object to a TimeSeriesId object."""
        return query.to_timeseries_id()

    @staticmethod
    def from_tuple(t: Tuple, column_level_names: Optional[List[str]] = None) -> TimeSeriesId:
        """Convert a tuple to a TimeSeriesId object."""
        if not column_level_names:
            return TimeSeriesId(
                quantity=t[0],
                group=t[1],
                name=t[2],
                chainage=t[3],
                tag=t[4],
                duplicate=t[5],
                derived=t[6],
            )
        else:
            return TimeSeriesId(**dict(zip(column_level_names, t)))

    @staticmethod
    def to_multiindex(timeseries_ids: List[TimeSeriesId], compact=False) -> pd.MultiIndex:
        """Convert a list of TimeSeriesId objects to a pandas MultiIndex.

        Parameters
        ----------
        timeseries_ids : List[TimeSeriesId]
            The list of TimeSeriesId objects to convert.
        compact : bool, optional
            Whether to compact the MultiIndex by removing redundant levels, by default False

        Returns
        -------
        pd.MultiIndex
            The converted MultiIndex.

        """
        index = pd.MultiIndex.from_tuples(
            [tsid.astuple() for tsid in timeseries_ids],
            names=["quantity", "group", "name", "chainage", "tag", "duplicate", "derived"],
        )

        if not compact:
            return index

        for field in fields(TimeSeriesId):
            level_values = index.get_level_values(field.name)
            is_only_one_unique_value = len(level_values.unique()) == 1
            if not is_only_one_unique_value:
                continue
            level_value = level_values[0]
            is_all_default_values = (level_value == field.default) or (
                level_value != level_value and field.default != field.default
            )
            if is_all_default_values:
                index = index.droplevel(field.name)

        return index

    @staticmethod
    def from_multiindex(index: pd.MultiIndex) -> List[TimeSeriesId]:
        """Convert a pandas MultiIndex to a list of TimeSeriesId objects."""
        if isinstance(index[0], tuple):
            if TimeSeriesId._is_multiindex_complete(index):
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
            else:
                # Assumes default values for missing fields
                available_fields = TimeSeriesId._get_multiindex_as_list_of_dicts(index)
                return [TimeSeriesId(**v) for v in available_fields]

        elif isinstance(index[0], TimeSeriesId):
            return index.to_list()
        else:
            raise ValueError(
                f"Cannot convert index of type '{type(index[0])}' to list of TimeSeriesId objects"
            )

    @staticmethod
    def _get_multiindex_as_list_of_dicts(index: pd.MultiIndex) -> List[dict]:
        """Convert a pandas MultiIndex to a list of dicts, where keys are the level name and values are the column names."""
        return [dict(zip(index.names, col)) for col in index.to_numpy()]

    @staticmethod
    def _is_multiindex_complete(index: pd.MultiIndex) -> bool:
        """Check whether the levels of a MultiIndex match the fields of TimeSeriesId."""
        index_fields = set(index.names)
        timeseries_id_fields = set([field.name for field in fields(TimeSeriesId)])
        return index_fields == timeseries_id_fields

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
            The index of the element within the IRes1DDataItem.

        """
        quantity = m1d_dataitem.Quantity.Id
        group = TimeSeriesIdGroup.from_m1d_data_item(m1d_dataitem)

        chainage = float("nan")
        if m1d_dataitem.IndexList is not None:
            chainages = m1d_dataset.GetChainages(m1d_dataitem)
            chainage = chainages[element_index]

        # DataItem objects on this DataSet have an ItemTypeGroup set to GlobalItem
        if "DHI.Mike1D.ResultDataAccess.Epanet.Res1DTypedReach" in repr(m1d_dataset.__class__):
            group = TimeSeriesIdGroup.REACH

        item_id = m1d_dataitem.ItemId
        if group == TimeSeriesIdGroup.STRUCTURE:
            name = item_id
            tag = TimeSeriesId.get_dataset_name(m1d_dataset, None)
        elif group == TimeSeriesIdGroup.REACH:
            name = TimeSeriesId.get_dataset_name(m1d_dataset, item_id)
            tag = TimeSeriesId.create_reach_span_tag(m1d_dataset)
        else:
            name = TimeSeriesId.get_dataset_name(m1d_dataset, item_id)
            tag = ""

        return TimeSeriesId(
            quantity=quantity,
            group=group,
            name=name,
            chainage=chainage,
            tag=tag,
        )

    @staticmethod
    def create_reach_span_tag(m1d_dataset) -> str:
        """Create a tag for an IRes1DReach object based on its chainage span.

        Parameters
        ----------
        m1d_dataset : IRes1DReach
            The MIKE 1D reach to create a tag for.

        Returns
        -------
        str
            The tag for the reach (e.g. '0.0-100.0')

        """
        if not hasattr(m1d_dataset, "GridPoints"):
            return ""

        if m1d_dataset.GridPoints.Count == 0:
            return ""

        start_gp = m1d_dataset.GridPoints[0]
        end_gp = m1d_dataset.GridPoints[m1d_dataset.GridPoints.Count - 1]

        tag = TimeSeriesId.create_reach_span_tag_from_gridpoints(start_gp, end_gp)
        return tag

    @staticmethod
    def create_reach_span_tag_from_gridpoints(start_gp, end_gp) -> str:
        """Create a tag for an IRes1DReach object based on its start and end gridpoints.

        Parameters
        ----------
        start_gp : IRes1DGridPoint
            The MIKE 1D gridpoint at the start of the reach.
        end_gp : IRes1DGridPoint
            The MIKE 1D gridpoint at the end of the reach.

        Returns
        -------
        str
            The tag for the reach (e.g. '0.0-100.0')
        """
        return f"{start_gp.Chainage:.1f}-{end_gp.Chainage:.1f}"

    @staticmethod
    def from_result_quantity(result_quantity: ResultQuantity) -> TimeSeriesId:
        """Create a TimeSeriesId object from a ResultQuantity object.

        Note: this method assumes there are no duplicates (e.g. duplicate = 0). To get the
        unique TimeSeriesId of a ResultQuantity, access its timeseries_id property.
        """
        result_location = result_quantity.result_location
        nan = float("nan")

        group = result_location._group
        quantity = result_quantity._name
        name = getattr(result_location, "_name", "")
        tag = getattr(result_location, "_tag", "")
        chainage = getattr(result_location, "chainage", nan)
        chainage = nan if chainage == DELETE_VALUE else chainage

        return TimeSeriesId(
            quantity=quantity,
            group=group,
            name=name,
            chainage=chainage,
            tag=tag,
        )

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
            The delimiter to use between the item id and the name

        """
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

    @staticmethod
    def try_from_obj(obj: Any) -> TimeSeriesId:
        """Try to convert an object to a TimeSeriesId object.

        Parameters
        ----------
        obj : Any
            The object to convert to a TimeSeriesId.

        Returns
        -------
        TimeSeriesId
            The converted TimeSeriesId object.

        """
        if isinstance(obj, TimeSeriesId):
            return obj
        elif isinstance(obj, tuple):
            return TimeSeriesId.from_tuple(obj)
        else:
            raise ValueError(f"Cannot convert type '{type(obj)}' to TimeSeriesId")
