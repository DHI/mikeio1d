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

    @property
    def chainage(self):
        return self._chainage

    def __repr__(self):
        name = self._name
        chainage = self._chainage
        quantity = self._quantity

        return (
            NAME_DELIMITER.join([quantity, name, f'{chainage:g}'])
            if chainage is not None else
            NAME_DELIMITER.join([quantity, name])
        )
