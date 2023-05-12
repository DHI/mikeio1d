from .data_entry import DataEntry

from DHI.Mike1D.MikeIO import DataEntry as DataEntryNet


class ResultQuantity:
    """
    Class for wrapping a single ResultData data item quantity.

    ResultQuantity objects are the last attributes assigned to a network.
    They have the ability to add a query.

    Parameters
    ----------
    result_location: ResultLocation
        ResultLocation object, which could be node, catchment, grid point, or global data item.
    data_item: IDataItem
        MIKE 1D IDataItem object.
    res1d : Res1D
        Res1D object the quantity belongs to.

    Attributes
    ----------
    element_index : int
        An integer giving an element index into the data item
        which gives the concrete time series for given location.
    """

    def __init__(self, result_location, data_item, res1d):
        self.result_location = result_location
        self.data_item = data_item
        self.res1d = res1d
        self.element_index = 0

    def add(self):
        """ Add a query to ResultNetwork.queries based on the data item. """
        self.result_location.add_query(self.data_item)

    def read(self):
        """ Read the time series data into a data frame. """
        query = self.get_query()
        return self.res1d.read(query)

    def plot(self, **kwargs):
        """ Plot the time series data. """
        df = self.read()
        ax = df.plot(**kwargs)
        quantity = self.data_item.Quantity
        ax.set_xlabel('Time')
        ax.set_ylabel(f'{quantity.Description} [$\\mathrm{{{quantity.EumQuantity.UnitAbbreviation}}}$]')
        return ax

    def to_dataframe(self):
        """ Get a time series as a data frame. """
        return self.read()

    def to_csv(self, file_path, time_step_skipping_number=1):
        """ Extract time series data into a csv file. """
        query = self.get_query()
        self.res1d.to_csv(file_path, query, time_step_skipping_number)

    def to_dfs0(self, file_path, time_step_skipping_number=1):
        """ Extract time series data into a dfs0 file. """
        query = self.get_query()
        self.res1d.to_dfs0(file_path, query, time_step_skipping_number)

    def to_txt(self, file_path, time_step_skipping_number=1):
        """ Extract time series data into a txt file. """
        query = self.get_query()
        self.res1d.to_txt(file_path, query, time_step_skipping_number)

    def get_query(self):
        """ Get query corresponding to ResultQuantity. """
        return self.result_location.get_query(self.data_item)

    def get_data_entry(self):
        """ Get DataEntry corresponding to ResultQuantity. """
        return DataEntry(self.data_item, self.element_index)

    def get_data_entry_net(self):
        """ Get DataEntryNet corresponding to ResultQuantity. """
        return DataEntryNet(self.data_item, self.element_index)
