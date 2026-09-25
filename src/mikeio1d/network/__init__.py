"""Build a graph-shaped network from a result file.

A result file describes a network as locations with the names the model gave
them: a node id, or a reach and a distance along it. This module turns that into
a :class:`Network`: a networkx graph of those locations, addressed by the same
names, that reads the timeseries each location holds only when asked for them.

The module needs ``networkx`` and ``xarray``, which the ``network`` extra
installs::

    pip install mikeio1d[network]

Examples
--------
>>> from mikeio1d.network import Network
>>> network = Network.open("tests/testdata/network.res1d")  # doctest: +SKIP
>>> network.resolve("101")  # doctest: +SKIP
>>> network.read([("101", "WaterLevel")])  # doctest: +SKIP
"""

try:
    import networkx
    import xarray
except ImportError as err:
    # Checked here rather than left to the first bare import inside the module,
    # so the message names the extra to install rather than the module that was
    # missing.
    raise ImportError(
        "mikeio1d.network needs networkx and xarray, which the 'network' extra "
        "installs: pip install mikeio1d[network]"
    ) from err

from ._naming import Address
from ._network import Network
from ._types import Location
from ._types import NetworkReach
from ._types import ReachBreakPoint

__all__ = [
    "Address",
    "Location",
    "Network",
    "NetworkReach",
    "ReachBreakPoint",
]
