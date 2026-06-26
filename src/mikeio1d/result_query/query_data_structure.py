"""Module for QueryDataStructure class."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from ..res1d import Res1D

from math import isnan

from ..custom_exceptions import InvalidQuantity
from ..custom_exceptions import InvalidStructure
from ..various import NAME_DELIMITER
from .query_data_reach import QueryDataReach
from ..quantities import TimeSeriesId
from ..quantities import TimeSeriesIdGroup


class QueryDataStructure(QueryDataReach):
    """A query object that declares what structure data to extract from a .res1d file.

    Parameters
    ----------
    quantity: str
        e.g. 'DischargeInStructure'. Call res1d.quantities to get all quantities.
    structure: str
        Structure name.
    name: str
        Reach name where the structure is located.
    chainage: float
        Chainage value where the structure is located on reach.
    validate: bool
        Flag specifying to validate the query.

    Examples
    --------
    `QueryDataStructure('DischargeInStructure', 'structure1')` is a valid query.

    """

    def __init__(self, quantity, structure=None, name=None, chainage=None, validate=True):
        super().__init__(quantity, name, chainage, validate=validate)
        self._structure = structure

    @property
    def structure(self):
        """Structure name."""
        return self._structure

    def get_values(self, res1d: Res1D):
        """Get the time series data for the query."""
        self._check_invalid_quantity(res1d)

        result_structure = self._get_result_structure(res1d)

        self._check_invalid_structure_quantity(result_structure)
        data_item = result_structure._creator.get_data_item(self._quantity)

        values = data_item.CreateTimeSeriesData(0)

        self._check_invalid_values(values)

        self._update_location_info(result_structure)

        return self.from_dotnet_to_python(values)

    def to_timeseries_id(self) -> TimeSeriesId:
        """Convert the query to a TimeSeriesId object."""
        chainage = self.chainage
        if chainage is None or chainage == "":
            chainage = float("nan")
        tsid = TimeSeriesId(
            quantity=self.quantity,
            group=TimeSeriesIdGroup.STRUCTURE,
            name=self.structure,
            chainage=chainage,
            tag=self.name,
        )
        return tsid

    @staticmethod
    def from_timeseries_id(timeseries_id: TimeSeriesId) -> QueryDataStructure:
        """Convert a TimeSeriesId object to a QueryDataStructure object."""
        chainage = timeseries_id.chainage
        if isnan(chainage):
            chainage = None
        return QueryDataStructure(
            quantity=timeseries_id.quantity,
            structure=timeseries_id.name,
            name=timeseries_id.tag,
            chainage=chainage,
            validate=False,
        )

    def _update_query(self, res1d):
        result_structure = self._get_result_structure(res1d)
        self._update_location_info(result_structure)

    def _get_result_structure(self, res1d):
        self._check_invalid_structure(res1d)
        result_structure = res1d.structures[self._structure]
        return result_structure

    def _check_invalid_structure(self, res1d):
        if self._structure not in res1d.structures:
            raise InvalidStructure(str(self))

    def _check_invalid_structure_quantity(self, result_structure):
        if self._quantity not in result_structure._creator.data_items_dict:
            raise InvalidQuantity(str(self))

    def _update_location_info(self, result_structure):
        if self._name is None:
            self._name = result_structure.reach.Name

        if self._chainage is None:
            self._chainage = result_structure.chainage

    def __repr__(self):
        """Return a string representation of the query."""
        structure = self._structure
        name = self._name
        chainage = self._chainage
        quantity = self._quantity

        if name is None and chainage is None:
            return NAME_DELIMITER.join([quantity, structure])

        if chainage is None:
            return NAME_DELIMITER.join([quantity, structure, name])

        return NAME_DELIMITER.join([quantity, structure, name, f"{chainage:g}"])
