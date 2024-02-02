import clr
import warnings

from collections.abc import Iterable

from System import Enum
from DHI.Mike1D.Generic import PredefinedQuantity

NAME_DELIMITER = ":"


def mike1d_quantities():
    """
    Returns all predefined Mike1D quantities.
    Useful for knowing what quantity string to query.
    """
    return [quantity for quantity in Enum.GetNames(clr.GetClrType(PredefinedQuantity))]


def try_import_geopandas():
    """
    Try 'import geopandas as gpd' and raise ImportError if not installed.
    """
    try:
        import geopandas as gpd
    except ImportError:
        message = "This functionality requires installing the optional dependency geopandas."
        raise ImportError(message)
    return gpd


def try_import_shapely():
    """
    Try 'import shapely' and raise ImportError if not installed.
    """
    try:
        import shapely
    except ImportError:
        message = "This functionality requires installing the optional dependency shapely."
        raise ImportError(message)
    return shapely


def pyproj_crs_from_projection_string(projection_string: str):
    """
    Convert a projection string to a pyproj CRS object.
    """
    from pyproj import CRS

    try:
        return CRS.from_string(projection_string)
    except Exception:
        warnings.warn("Could not parse projection string. Returning None.")
        return None


def make_list_if_not_iterable(obj) -> list:
    """
    Boxes non-iterable objects into a list. Only intended to clean user input once.

    For strings, the string is boxed into a list.
    For None, an empty list is returned.

    Parameters
    ----------
    obj : object
        Object to box.

    Returns
    -------
    list
        List with one element if obj is not iterable, otherwise obj.
    """
    if obj is None:
        return []

    if not isinstance(obj, Iterable):
        return [obj]

    if isinstance(obj, str):
        return [obj]

    return obj
