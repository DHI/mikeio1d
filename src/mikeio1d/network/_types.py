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
class NetworkNode:
    """A node in a network, such as a junction or a reservoir.

    Attributes
    ----------
    id : str
        The id the model gave the node, unique within the network.
    """

    id: str


@dataclass(frozen=True)
class ReachBreakPoint:
    """A location along a reach, between its two end nodes.

    Attributes
    ----------
    reach_id : str
        The reach the break point sits on.
    distance : float or None
        Position along the reach, in the reach's own frame, or ``None`` where it
        is genuinely unknown (a link-node reach with no known length). It need
        not be measured from the start node: a MIKE river reach reports its
        chainage, a coordinate along the whole branch, so the distance from the
        start node is ``distance - reach.start_distance``. A break point with an
        unknown distance has a graph node of its own, but no address names it.
    """

    reach_id: str
    distance: float | None

    @property
    def id(self) -> tuple[str, float | None]:
        """``(reach_id, distance)``, which uniquely locates the break point."""
        return (self.reach_id, self.distance)


@dataclass(frozen=True)
class NetworkReach:
    """A directed connection between two nodes, and the break points along it.

    Attributes
    ----------
    id : str
        The id the model gave the reach, unique within the network.
    start, end : NetworkNode
        The start (upstream) and end (downstream) nodes.
    length : float or None
        Total length in network units, or ``None`` where it is undefined. Reach
        length matters in some domains (rivers, sewer networks) and not in
        others (link-node water distribution models).
    start_distance : float
        Position of the start node, in the frame :attr:`breakpoints` are placed
        in. Zero where they are measured from the reach's own start; a MIKE river
        reach places them at their chainage, so it can begin thousands of metres
        in - or below zero.
    breakpoints : tuple of ReachBreakPoint
        Ascending by distance from the start node, and :class:`Network` relies
        on it: the first and last are the reach's outermost, and consecutive
        differences are edge lengths, which a backwards pair would report as
        negative. A break point is keyed by its reach's id, so a reach that has
        any gets its own chain of graph nodes and stays distinct from a parallel
        reach between the same two nodes. A reach with none is a single
        start-to-end edge instead, and two such reaches between one pair of
        nodes cannot be told apart - :class:`Network` refuses them rather than
        dropping one.
    """

    id: str
    start: NetworkNode
    end: NetworkNode
    length: float | None = None
    start_distance: float = 0.0
    breakpoints: tuple[ReachBreakPoint, ...] = ()

    @property
    def end_distance(self) -> float | None:
        """Position of the end node, or ``None`` where the length is undefined."""
        return None if self.length is None else self.start_distance + self.length

    @property
    def n_breakpoints(self) -> int:
        """Number of break points in the reach."""
        return len(self.breakpoints)


@dataclass(frozen=True)
class Location:
    """A location a network has, as :meth:`Network.resolve` answers for it.

    Attributes
    ----------
    address : str or tuple[str, float]
        The network's own spelling of the location, which the rest of the
        network takes. A distance is the one the file stores, not the one asked
        for.
    quantities : tuple of str
        The quantity IDs readable there. Empty is an answer: the location is
        in the network but carries nothing of its own.
    node : int
        The integer :attr:`Network.graph` and :meth:`Network.to_dataset` label
        the location with. ``graph.nodes[node]["alias"]`` is the address.
    """

    address: Address
    quantities: tuple[str, ...]
    node: int
