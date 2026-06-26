"""Module for custom exceptions."""


class DataDimensionMismatch(ValueError):
    """Exception raised for data matrices in the x dimension that do not all match in the data list."""

    def __init__(self):
        self.message = (
            "Data matrices in the x dimension do not all match in the data list."
            "Data is a list of matrices [t, x]."
        )
        super().__init__(self.message)


class ItemNumbersError(ValueError):
    """Exception raised for errors in the item numbers."""

    def __init__(self, n_items_file):
        super().__init__(
            f"item numbers must be (a list of) integers between 0 and {n_items_file-1}."
        )


class ItemsError(ValueError):
    """Exception raised for errors in the items."""

    def __init__(self, n_items_file):
        super().__init__(
            f"'items' must be (a list of) integers between 0 and {n_items_file-1} or str."
        )


class InvalidDataType(ValueError):
    """Exception raised for invalid data type."""

    def __init__(self):
        super().__init__("Invalid data type. Choose np.float32 or np.float64")


class InvalidGeometry(ValueError):
    """Exception raised for invalid geometry."""

    def __init__(self, message="Invalid operation for this type of geometry"):
        super().__init__(message)


class InvalidDataValueType(ValueError):
    """Exception raised for invalid data value type."""

    def __init__(self):
        super().__init__(
            "Invalid data type. Choose 'Instantaneous', 'Accumulated', 'StepAccumulated', "
            "'MeanStepBackward', or 'MeanStepForward'"
        )


class NoDataForQuery(ValueError):
    """Exception raised for invalid query."""

    def __init__(self, query_string):
        super().__init__(f"Invalid query {query_string}")


class InvalidQuantity(ValueError):
    """Exception raised for invalid quantity."""

    def __init__(self, message="Invalid quantity."):
        super().__init__(message)


class InvalidStructure(ValueError):
    """Exception raised for invalid structure."""

    def __init__(self, message="Invalid structure ID."):
        super().__init__(message)
