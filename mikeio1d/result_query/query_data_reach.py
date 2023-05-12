from ..various import NAME_DELIMITER
from .query_data import QueryData


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

        if validate:
            self._validate()

    def _validate(self):
        super()._validate()

        if self.chainage is not None and not isinstance(self.chainage, (int, float)):
            raise TypeError("Argument 'chainage' must be either None or a number.")

        if self.name is None and self.chainage is not None:
            raise ValueError("Argument 'chainage' cannot be set if name is None.")

    def get_values(self, res1d):
        self._check_invalid_quantity(res1d)

        name = self._name
        chainage = self._chainage
        quantity = self._quantity

        values = (
            res1d.query.GetReachValues(name, chainage, quantity)
            if chainage is not None else
            res1d.query.GetReachStartValues(name, quantity)
        )

        self._check_invalid_values(values)

        return self.from_dotnet_to_python(values)

    def _update_query(self, res1d):
        name = self._name
        chainage = self._chainage
        quantity = self._quantity

        if chainage is None:
            return

        reach = res1d.searcher.FindReach(name, chainage)
        if reach is None:
            return

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
        return self._chainage

    def __repr__(self):
        name = self._name
        chainage = self._chainage
        quantity = self._quantity

        return (
            NAME_DELIMITER.join([quantity, name, f'{chainage:g}'])
            if chainage is not None and chainage != self.delete_value else
            NAME_DELIMITER.join([quantity, name])
        )
