from __future__ import annotations

"""
Experimental xvec integration.

This module provides a small helper to convert a :class:`mikeio1d.Res1D` into
an :class:`xarray.DataArray` with a geometry coordinate backed by
:xclass:`xvec.GeometryIndex`.

Implementation notes
- Reuses the `experimental._xarray.to_dataarray` dense conversion so the feature
  coordinates `group`, `quantity`, `chainage` and `name` are present.
- Maps the `group` coordinate to the corresponding ResultLocations collection
  (nodes, reaches, catchments) and looks up the object by `name`.
- For reaches: if `chainage` is present and not NaN the code indexes the
  corresponding ResultReach with the chainage to obtain a ResultGridPoint.
- Minimal, fast, and maintainable: no per-item try/except noise; missing
  geometries become an empty `GeometryCollection` placeholder so the index
  remains consistent.
"""

from operator import ge
from typing import Any, List, Optional, cast, TYPE_CHECKING, TypeIs

if TYPE_CHECKING:
    import shapely
    from shapely.geometry.base import BaseGeometry

import math
import xarray as xr
import xvec
import pandas as pd
from shapely.geometry import GeometryCollection

from ..res1d import Res1D
from ..result_network import (
    ResultGridPoint,
    ResultReach,
    ResultReaches,
    ResultNode,
    ResultNodes,
    ResultCatchment,
    ResultCatchments,
    ResultLocations,
)
from ._xarray import to_dataarray as _to_dataarray_xarray
from ..quantities import TimeSeriesIdGroup


def to_dataarray_xvec(res: Res1D) -> xr.DataArray:
    """Convert a Res1D object to an xarray DataArray with an xvec GeometryIndex.

    The DataArray will have dimensions (`time`, `geometry`). Note that the geometry index is not guaranteed to be unique: identical geometries
    may appear multiple times and will be preserved in the index. The DataArray also
    retains the original feature coordinates produced by the underlying conversion
    (quantity, group, chainage, name), so those coordinates are available alongside
    the geometry coordinate.

    Parameters
    ----------
    res : Res1D
        The Res1D object.

    Returns
    -------
    xr.DataArray
        DataArray with dimensions (`time`, `geometry`)
        coordinate registered in the xindex.

    Examples
    --------
    >>> da = to_dataarray_xvec(res)
    >>> da

    Plot all node water levels at first time step:
    >>> (da
        .where(
            (da.quantity == "WaterLevel") &
            (da.group == "Node")
        )
        .isel(time=0)
        .xvec.plot()
    )

    Get values within point radius:
    >>> point = Point(-687763.099, -1056440.1).buffer(100)
    >>> da.xvec.query("geometry", [point], predicate="intersects")
    """
    import shapely

    da = _to_dataarray_xarray(res)

    groups = cast(xr.DataArray, da.coords["group"])
    groups = cast(list[str], groups.to_numpy().astype(str).tolist())

    names = cast(xr.DataArray, da.coords["name"])
    names = cast(list[str], names.to_numpy().astype(str).tolist())

    chainages = cast(xr.DataArray, da.coords["chainage"])
    chainages = cast(list[float], chainages.to_numpy().astype(float).tolist())

    geometries: list[BaseGeometry] = []

    group_to_locations_group = {
        str(TimeSeriesIdGroup.NODE): res.network.nodes,
        str(TimeSeriesIdGroup.REACH): res.network.reaches,
        str(TimeSeriesIdGroup.CATCHMENT): res.network.catchments,
    }

    groups = [group_to_locations_group.get(g, None) for g in groups]

    def is_result_reaches(obj: ResultLocations) -> TypeIs[ResultReaches]:
        return isinstance(obj, ResultReaches)

    def is_result_nodes(obj: ResultLocations) -> TypeIs[ResultNodes]:
        return isinstance(obj, ResultNodes)

    def is_result_catchments(obj: ResultLocations) -> TypeIs[ResultCatchments]:
        return isinstance(obj, ResultCatchments)

    for group, name, chainage in zip(groups, names, chainages):
        geom = GeometryCollection()

        if group is None:
            raise ValueError(f"Unknown group '{group}' in time series.")

        if not name:
            raise ValueError(f"A name is missing in '{group}'.")

        if is_result_reaches(group):
            reach = cast(ResultReach, group[name])
            is_gridpoint = not math.isnan(chainage)
            if is_gridpoint:
                gridpoint = reach[chainage]
                if not isinstance(gridpoint.xcoord, float) or not isinstance(
                    gridpoint.ycoord, float
                ):
                    raise ValueError(f"Missing geometry for reach '{name}' at chainage {chainage}.")
                geom = shapely.Point(gridpoint.xcoord, gridpoint.ycoord)
            else:
                geom = reach.geometry.to_shapely()
        elif is_result_nodes(group):
            node = cast(ResultNode, group[name])
            geom = node.geometry.to_shapely()
        elif is_result_catchments(group):
            catchment = cast(ResultCatchment, group[name])
            geom = catchment.geometry.to_shapely()
        else:
            raise ValueError(f"Unsupported locations group type: {type(group)}")

        geometries.append(geom)

    da = da.assign_coords(geometry=("feature", geometries))
    da = da.swap_dims({"feature": "geometry"})
    da = da.xvec.set_geom_indexes("geometry")

    return da
