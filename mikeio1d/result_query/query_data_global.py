from .query_data import QueryData


class QueryDataGlobal(QueryData):
    """A query object that declares what global data to extract from a .res1d file.

    Parameters
    ----------
    quantity: str
        e.g. 'TimeStep'. Call res1d.quantities to get all quantities.
    validate: bool
        Flag specifying to validate the query.

    Examples
    --------
    `QueryDataGlobal('TimeStep')` is a valid query.
    """

    def __init__(self, quantity, validate=True):
        super().__init__(quantity, validate=validate)

    def get_values(self, res1d):
        self._check_invalid_quantity(res1d)

        data_item = res1d.global_data[self._quantity]
        values = data_item.CreateTimeSeriesData(0)

        self._check_invalid_values(values)

        return self.from_dotnet_to_python(values)

    def __repr__(self):
        return self._quantity
