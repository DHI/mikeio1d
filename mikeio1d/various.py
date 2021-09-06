import clr

from System import Enum
from DHI.Mike1D.Generic import PredefinedQuantity

NAME_DELIMITER = ":"


def mike1d_quantities():
    """
    Returns all predefined Mike1D quantities.
    Useful for knowing what quantity string to query.
    """
    return [quantity for quantity in Enum.GetNames(clr.GetClrType(PredefinedQuantity))]
