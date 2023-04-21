class DataEntry(object):
    """Class storing a Mike1D data item and a corresponding element index"""

    def __init__(self, data_item, element_index):
        self.data_item = data_item
        self.element_index = element_index
