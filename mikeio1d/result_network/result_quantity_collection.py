from .result_quantity import ResultQuantity


class ResultQuantityCollection(ResultQuantity):
    """
    Class for dealing with a collection ResultQuantity objects.

    ResultQuantityCollection objects are the attributes assigned to a network
    type like nodes, catchments, etc. For example, res1d.nodes.WaterLevel
    They have the ability to add queries.

    Parameters
    ----------
    result_quantities: list of ResultQuantity objects
        A list of ResultQuantity objects having the same quantity id.
    res1d : Res1D
        Res1D object the quantity belongs to.
    """

    def __init__(self, result_quantities, res1d):
        self.result_quantities = result_quantities
        self.res1d = res1d

    def add(self):
        """
        Add queries to ResultNetwork.queries from a list of result quantities.
        """
        for result_quantity in self.result_quantities:
            result_quantity.add()

    def read(self):
        """Read the time series data into a data frame."""
        timeseries_ids = [q.timeseries_id for q in self.result_quantities]
        return self.res1d.read(timeseries_ids)

    def plot(self):
        """Plot the time series data."""
        if len(self.result_quantities) <= 0:
            return

        self.data_item = self.result_quantities[0].data_item
        ResultQuantity.plot(self)

    def get_query(self):
        """Get queries corresponding to ResultQuantityCollection."""
        queries = []
        for result_quantity in self.result_quantities:
            query = result_quantity.get_query()
            queries.append(query)
        return queries
