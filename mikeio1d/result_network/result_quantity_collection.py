class ResultQuantityCollection:
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
