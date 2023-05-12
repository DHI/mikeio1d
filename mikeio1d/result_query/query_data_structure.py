from ..custom_exceptions import InvalidQuantity
from ..custom_exceptions import InvalidStructure
from ..various import NAME_DELIMITER
from .query_data_reach import QueryDataReach


class QueryDataStructure(QueryDataReach):
    """A query object that declares what structure data to extract from a .res1d file.

    Parameters
    ----------
    quantity: str
        e.g. 'DischargeInStructure'. Call res1d.quantities to get all quantities.
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

    def get_values(self, res1d):
        self._check_invalid_quantity(res1d)

        result_structure = self._get_result_structure(res1d)

        self._check_invalid_structure_quantity(result_structure)
        data_item = result_structure.get_data_item(self._quantity)

        values = data_item.CreateTimeSeriesData(0)

        self._check_invalid_values(values)

        self._update_location_info(result_structure)

        return self.from_dotnet_to_python(values)

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
        if self._quantity not in result_structure.data_items_dict:
            raise InvalidQuantity(str(self))

    def _update_location_info(self, result_structure):
        if self._name is None:
            self._name = result_structure.reach.Name

        if self._chainage is None:
            self._chainage = result_structure.chainage

    def __repr__(self):
        structure = self._structure
        name = self._name
        chainage = self._chainage
        quantity = self._quantity

        if name is None and chainage is None:
            return NAME_DELIMITER.join([quantity, structure])

        if chainage is None:
            return NAME_DELIMITER.join([quantity, structure, name])

        return NAME_DELIMITER.join([quantity, structure, name, f'{chainage:g}'])
