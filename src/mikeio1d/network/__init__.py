"""Build a graph-shaped network from a result file.

A result file describes a network as locations with the names the model gave
them: a node id, or a reach and a distance along it. This module turns that into
a :class:`Network` - a networkx graph whose nodes are flat integers, carrying the
timeseries each location holds - and translates between the two namings.

The module is provisional. It needs ``networkx`` and ``xarray``, which the
``network`` extra installs::

    pip install mikeio1d[network]

Examples
--------
>>> from mikeio1d.network import Network
>>> network = Network.open("tests/testdata/network.res1d")  # doctest: +SKIP
>>> node = network.find(node="101")  # doctest: +SKIP
>>> network.to_dataframe()  # doctest: +SKIP
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

from ._network import Network
from ._types import BasicNode, BasicReach, NetworkNode, NetworkReach, ReachBreakPoint

__all__ = [
    "BasicNode",
    "BasicReach",
    "Network",
    "NetworkNode",
    "NetworkReach",
    "ReachBreakPoint",
]
