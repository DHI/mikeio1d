"""Module for QueryDataReach class."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from ..res1d import Res1D

from math import isnan

from ..various import NAME_DELIMITER
from ..various import DELETE_VALUE
from .query_data import QueryData
from ..quantities import TimeSeriesId
from ..quantities import TimeSeriesIdGroup


class QueryDataReach(QueryData):
    """A query object that declares what reach data to extract from a .res1d file.

    Parameters
    ----------
    quantity: str
        e.g. 'WaterLevel' or 'Discharge'. Call res1d.quantities to get all quantities.
    name: str
        Reach name.
    chainage: float
        Chainage value.
    validate: bool
        Flag specifying to validate the query.

    Examples
    --------
    `QueryDataReach('WaterLevel', 'reach1', 10)` is a valid query.

    """

    def __init__(self, quantity, name=None, chainage=None, validate=True):
        super().__init__(quantity, name, validate=False)
        self._chainage = chainage
        self._m1d_dataset = None

        if validate:
            self._validate()

    def _validate(self):
        super()._validate()

        if self.chainage is not None and not isinstance(self.chainage, (int, float)):
            raise TypeError("Argument 'chainage' must be either None or a number.")

        if self.name is None and self.chainage is not None:
            raise ValueError("Argument 'chainage' cannot be set if name is None.")

    def get_values(self, res1d: Res1D):
        """Get the time series data for the query."""
        self._check_invalid_quantity(res1d)

        name = self._name
        chainage = self._chainage
        quantity = self._quantity

        values = (
            res1d.query.GetReachValues(name, chainage, quantity)
            if chainage is not None
            else res1d.query.GetReachStartValues(name, quantity)
        )

        self._check_invalid_values(values)

        return self.from_dotnet_to_python(values)

    def to_timeseries_id(self) -> TimeSeriesId:
        """Convert the query to a TimeSeriesId object."""
        quantity = self.quantity
        group = TimeSeriesIdGroup.REACH
        name = self.name
        tag = TimeSeriesId.create_reach_span_tag(self._m1d_dataset)
        if self.chainage is not None:
            return TimeSeriesId(
                quantity=quantity,
                group=group,
                name=name,
                chainage=self.chainage,
                tag=tag,
            )
        else:
            return TimeSeriesId(
                quantity=quantity,
                group=group,
                name=name,
                tag=tag,
            )

    @staticmethod
    def from_timeseries_id(timeseries_id: TimeSeriesId) -> QueryDataReach:
        """Convert a TimeSeriesId object to a QueryDataReach object."""
        chainage = timeseries_id.chainage
        if isnan(chainage):
            chainage = None
        return QueryDataReach(timeseries_id.quantity, timeseries_id.name, chainage, validate=False)

    def _update_query(self, res1d):
        name = self._name
        chainage = self._chainage
        quantity = self._quantity

        if chainage is None:
            return

        reach = res1d.searcher.FindReach(name, chainage)
        if reach is None:
            return

        self._m1d_dataset = reach

        data_item = res1d.query.FindDataItem(reach, quantity)
        if data_item is None:
            return

        closest_element_index = res1d.query.FindClosestElement(reach, chainage, data_item)
        if closest_element_index == -1:
            return

        gridpoint_index = list(data_item.IndexList)[closest_element_index]
        gridpoint = list(reach.GridPoints)[gridpoint_index]

        self._chainage = gridpoint.Chainage

    @property
    def chainage(self):
        """Chainage value."""
        return self._chainage

    def __repr__(self):
        """Return a string representation of the query."""
        name = self._name
        chainage = self._chainage
        quantity = self._quantity

        return (
            NAME_DELIMITER.join([quantity, name, f"{chainage:g}"])
            if chainage is not None and chainage != DELETE_VALUE
            else NAME_DELIMITER.join([quantity, name])
        )
