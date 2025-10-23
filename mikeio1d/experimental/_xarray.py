from __future__ import annotations

import xarray as xr

from ..res1d import Res1D


def to_dataarray(res: Res1D) -> xr.DataArray:
    """Convert a Res1D object to an xarray DataArray.

    The DataArray will have dimensions ("time", "feature"), where "feature"
    corresponds to an index of time series in the Res1D object. The feature dimension
    has coordinates for mapping to modeler semantics such as quantity, group, and id.

    Parameters
    ----------
    res : Res1D
        The Res1D object

    Notes
    -----
    The feature dimension has no semantic meaning by itself. It exists to ensure a
    dense array, rather than a sparse array with many NaNs. Reaches have arbitrary
    number of gridpoints, which can each have an arbitrary set of quantities,
    resulting in a sparse data structure. Use the feature coordinates to filter
    and select data as needed.

    The feature dimension does not have a multilevel index since they are not supported
    by zarr. Additionally, DataTree was considered for handling sparsity where each location
    and quantity woudld be a separate DataSet, however, zarr does not scale well with many
    small arrays.

    Returns
    -------
    xr.DataArray
        The xarray DataArray object.

    Examples
    --------
    >>> from mikeio1d.experimental import to_dataarray
    >>> da = to_dataarray(res)
    >>> da = da.sel(quantity="WaterLevel", group="Reach")

    >>> da = da.where(da.chainage == 0, drop=True)
    >>> da = da.isel(time=slice(0, 10))
    """
    df = res.read(column_mode="all")
    da = xr.DataArray(df, dims=("time", "feature"))
    return da
