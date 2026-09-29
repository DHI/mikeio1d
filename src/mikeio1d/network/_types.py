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
class ReachBreakpoint:
    """A location along a reach, between its two end nodes.

    Attributes
    ----------
    reach_id : str
        The reach the breakpoint sits on.
    position : float
        Where the breakpoint sits along the reach, in the reach's own frame: a
        place, not a size. It need not be measured from the start node: a MIKE
        river reach reports its chainage, a coordinate along the whole branch,
        so the distance from the start node is
        ``position - reach.start_position``.
    """

    reach_id: str
    position: float

    @property
    def id(self) -> tuple[str, float]:
        """``(reach_id, position)``, which uniquely locates the breakpoint."""
        return (self.reach_id, self.position)


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
    breakpoints : tuple of ReachBreakpoint
        Ascending by position; consecutive differences are edge lengths. A reach
        with breakpoints gets its own chain of graph nodes. A reach with none
        is a single start-to-end edge, and :class:`Network` refuses two of those
        between the same pair of nodes.
    """

    id: str
    start: str
    end: str
    length: float | None = None
    start_position: float = 0.0
    breakpoints: tuple[ReachBreakpoint, ...] = ()

    @property
    def end_position(self) -> float | None:
        """Position of the end node, or ``None`` where the length is undefined."""
        return None if self.length is None else self.start_position + self.length

    @property
    def n_breakpoints(self) -> int:
        """Number of breakpoints in the reach."""
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
        The integer :attr:`Network.graph` and :meth:`Network.to_dataset` label
        the location with, which ``graph.nodes[graph_node]["address"]`` turns
        back into the address. Every location has one, a breakpoint too.
    """

    address: Address
    quantities: tuple[str, ...]
    graph_node: int
