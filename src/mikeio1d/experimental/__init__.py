"""
Experimental features for mikeio1d.

Note:
    Code in this module is not part of the public API.
    Use at your own risk. Functionality and interfaces may change or be removed at any time.

NetworkMapper and GenericNetwork used to live here. They mapped a Res1D onto a
generic graph, which mikeio1d.network now does with reach lengths, boundary
edges and the companion files an EPANET result comes with.
"""

from ._networkx import to_networkx
from ._xarray import to_dataarray
from ._xvec import to_dataarray_xvec

__all__ = ["to_dataarray", "to_dataarray_xvec", "to_networkx"]
