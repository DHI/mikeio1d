import clr
import warnings

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
