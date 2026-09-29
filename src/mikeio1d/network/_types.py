"""The elements a network's topology is made of.

Plain records: the loader fills them in from a result file, and
:class:`~mikeio1d.network.Network` builds its graph from them knowing nothing
about the file they came from. What a location carries is not recorded here -
that is the loader's series map to answer.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from ._naming import Address

from dataclasses import dataclass


@dataclass(frozen=True)
class NetworkReach:
    """A directed connection between two nodes, and the breakpoints along it.

    Attributes
    ----------
    id : str
        The id the model gave the reach, unique within the network. A
        structure's reach keeps the type prefix its file gives it, such as
        ``"Weir:119w1"`` or ``"Pump:115p1"``, which keeps a weir and a pump that
        share an id apart.
    start, end : str
        The ids of the start (upstream) and end (downstream) nodes.
    length : float or None
        Total length in network units, or ``None`` where it is undefined. Reach
        length matters in some domains (rivers, sewer networks) and not in
        others (link-node water distribution models).
    start_position : float
        Position of the start node, in the frame :attr:`breakpoints` are placed
        in. Zero where they are measured from the reach's own start; a MIKE river
        reach places them at their chainage, so it can begin thousands of metres
        in - or below zero.
    breakpoints : tuple of (str, float)
        The addresses of the breakpoints along the reach, each a
        ``(reach_id, position)`` pair as :meth:`Network.read` takes it.
        Ascending by position; consecutive differences are edge lengths. A reach
        with breakpoints gets its own chain of graph nodes. A reach with none
        is a single start-to-end edge, and :class:`Network` refuses two of those
        between the same pair of nodes.

    Examples
    --------
    >>> from mikeio1d.network import Network
    >>> network = Network.open("tests/testdata/network.res1d")
    >>> network.reaches["100l1"]  # doctest: +NORMALIZE_WHITESPACE
    NetworkReach(id='100l1', start='100', end='99', length=47.6827148432828,
        start_position=0.0, breakpoints=(('100l1', 0.0), ('100l1', 23.8413574216414),
        ('100l1', 47.6827148432828)))

    A breakpoint is an address as it stands:

    >>> network.read([(network.reaches["100l1"].breakpoints[1], "Discharge")]).shape
    (110, 1)
    """

    id: str
    start: str
    end: str
    length: float | None = None
    start_position: float = 0.0
    breakpoints: tuple[tuple[str, float], ...] = ()

    @property
    def end_position(self) -> float | None:
        """Position of the end node, or ``None`` where the length is undefined.

        Examples
        --------
        A MIKE river reach whose chainage starts below zero:

        >>> from mikeio1d.network import Network
        >>> river = Network.open("tests/testdata/network_river.res1d")
        >>> reach = river.reaches["basin_right"]
        >>> reach.start_position, reach.length, reach.end_position
        (-10.0, 730.0, 720.0)
        """
        return None if self.length is None else self.start_position + self.length

    @property
    def n_breakpoints(self) -> int:
        """Number of breakpoints in the reach.

        Examples
        --------
        >>> from mikeio1d.network import Network
        >>> network = Network.open("tests/testdata/network.res1d")
        >>> network.reaches["100l1"].n_breakpoints
        3
        """
        return len(self.breakpoints)


@dataclass(frozen=True)
class Location:
    """A location a network has, as :meth:`Network.resolve` answers for it.

    Attributes
    ----------
    address : str or tuple[str, float]
        The network's own spelling of the location, which the rest of the
        network takes. A position is the one the file stores, not the one asked
        for.
    quantities : tuple of str
        The quantity IDs readable there. Empty is an answer: the location is
        in the network but carries nothing of its own.
    graph_node : int
        The integer :meth:`Network.to_networkx` and :meth:`Network.to_dataset` label
        the location with, which ``graph.nodes[graph_node]["address"]`` turns
        back into the address. Every location has one, a breakpoint too.

    Examples
    --------
    >>> from mikeio1d.network import Network
    >>> network = Network.open("tests/testdata/network.res1d")
    >>> location = network.resolve(("100l1", 23.8), position_tol=0.1)
    >>> location.address, location.quantities
    (('100l1', 23.8413574216414), ('Discharge',))
    >>> network.to_networkx().nodes[location.graph_node]["address"]
    ('100l1', 23.8413574216414)
    """

    address: Address
    quantities: tuple[str, ...]
    graph_node: int
