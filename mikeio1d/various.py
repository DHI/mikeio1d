"""Various utility functions for mikeio1d."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Type
    from mikeio1d import Res1D
    from mikeio1d import Xns11

import clr
import warnings
import sys

from collections.abc import Iterable
from pathlib import Path

from System import Enum
from DHI.Mike1D.Generic import PredefinedQuantity


NAME_DELIMITER = ":"
DELETE_VALUE = -1e-30


def mike1d_quantities():
    """Return all predefined Mike1D quantities.

    Useful for knowing what quantity string to query.
    """
    return [quantity for quantity in Enum.GetNames(clr.GetClrType(PredefinedQuantity))]


def try_import_geopandas():
    """Try 'import geopandas as gpd' and raise ImportError if not installed."""
    try:
        import geopandas as gpd
    except ImportError:
        message = "This functionality requires installing the optional dependency geopandas."
        raise ImportError(message)
    return gpd


def try_import_shapely():
    """Try 'import shapely' and raise ImportError if not installed."""
    try:
        import shapely
    except ImportError:
        message = "This functionality requires installing the optional dependency shapely."
        raise ImportError(message)
    return shapely


def pyproj_crs_from_projection_string(projection_string: str):
    """Convert a projection string to a pyproj CRS object."""
    from pyproj import CRS

    try:
        return CRS.from_string(projection_string)
    except Exception:
        warnings.warn("Could not parse projection string. Returning None.")
        return None


def make_list_if_not_iterable(obj) -> list:
    """Boxes non-iterable objects into a list. Only intended to clean user input once.

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


def allow_nested_autocompletion_for_ipython(cls: Type):
    """Configure IPython to allow nested autocompletion for a class.

    See https://github.com/ipython/ipython/pull/13852
    """
    if "IPython" not in sys.modules:
        return

    from IPython.core import guarded_eval

    guarded_eval.EVALUATION_POLICIES["limited"].allowed_getattr.add(cls)


def open(file_name: str | Path, **kwargs) -> Res1D | Xns11:
    """Open a file type supported by MIKE IO 1D file."""
    # import here to avoid circular imports
    from mikeio1d.res1d import Res1D
    from mikeio1d.xns11 import Xns11

    if isinstance(file_name, str):
        file_name = Path(file_name)

    if not file_name.exists():
        raise FileNotFoundError(f"File not found: {file_name}")

    suffix = file_name.suffix.lower()
    file_name = str(file_name)

    if suffix in Res1D.get_supported_file_extensions():
        return Res1D(file_name, **kwargs)
    elif suffix in Xns11.get_supported_file_extensions():
        return Xns11(file_name, **kwargs)
