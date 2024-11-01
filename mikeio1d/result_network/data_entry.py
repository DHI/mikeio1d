"""DataEntry class."""

from DHI.Mike1D.MikeIO import DataEntry as DataEntryNet


class DataEntry(object):
    """Class storing a Mike1D data item and a corresponding element index.

    Parameters
    ----------
    data_item : IDataItem
        The Mike1D IDataItem object.
    element_index : int
        Element index of the specific timeseries within IDataItem object.
    m1d_dataset : IRes1DDataset, optional
        The associated Mike1D IRes1DDataset object, by default None.

    """

    def __init__(self, data_item, element_index, m1d_dataset=None):
        self.data_item = data_item
        self.element_index = element_index
        self.m1d_dataset = m1d_dataset

    def to_dotnet(self):
        """Convert to DataEntryNet object."""
        return DataEntryNet(self.data_item, self.element_index)

    def add_to_data_entries(self, data_entries):
        """Add this DataEntry to a DataEntryNet collection.

        Parameters
        ----------
        data_entries : DataEntryNet
            The DataEntryNet object to append this DataEntry to.

        """
        data_entry_net = self.to_dotnet()
        data_entries.Add(data_entry_net)
