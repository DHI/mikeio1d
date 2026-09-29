"""Match the names a model gave its locations to the graph's nodes.

A result file names a location the way the model did: a node id, or a reach and
a position along it. This module holds the rule for when two positions mean the
same place, the integer each name has in the graph, and the hints an error gives
for a name the network does not have.

:class:`~mikeio1d.network.Network` builds one of these from its graph and keeps
it for the lifetime of the network.
"""

from __future__ import annotations

import bisect
import math

from collections.abc import Mapping
from difflib import get_close_matches

import networkx as nx

from ._types import NetworkReach

# Tolerance for comparing positions along a reach, in whatever length unit the
# network uses. Two positions within it are the same place, which is what a
# tolerant lookup asks and what the graph builder asks of an edge whose ends
# coincide.
_POSITION_TOLERANCE = 1e-3

Address = str | tuple[str, float]
"""A location under the name its model gave it.

A plain ``str`` is a node id. A ``(reach_id, position)`` tuple is a breakpoint.
Nothing is both, so the shape says which it is.
"""


def _is_breakpoint(address: Address) -> bool:
    """Whether an address names a breakpoint rather than a node."""
    return isinstance(address, tuple)


class _Naming:
    """The addresses in a network, and their graph nodes, built once from a graph.

    Parameters
    ----------
    graph : nx.Graph
        The integer-labelled graph, each node carrying its ``address``.
    reaches : Mapping[str, NetworkReach]
        The network's reaches, by id, for telling a missing reach from a
        missing position on one.
    """

    def __init__(self, graph: nx.Graph, reaches: Mapping[str, NetworkReach]):
        self._graph_nodes: dict[Address, int] = {
            address: graph_node for graph_node, address in graph.nodes(data="address")
        }
        # Each reach's breakpoint positions, ascending, for bisect.
        self._positions: dict[str, list[float]] = {}
        for address in self._graph_nodes:
            if _is_breakpoint(address):
                self._positions.setdefault(address[0], []).append(address[1])
        for known in self._positions.values():
            known.sort()
        self._reaches = reaches

    @property
    def graph_nodes(self) -> Mapping[Address, int]:
        """Every address in the network, mapped to its graph node."""
        return self._graph_nodes

    def canonical(self, address: Address, *, position_tol: float | None = None) -> Address | None:
        """Give the network's own spelling of an address, or None if there is no such place.

        An exact hit answers immediately. Failing that, a breakpoint is matched
        on position within ``position_tol``, defaulting to
        :data:`_POSITION_TOLERANCE`, so a caller need not reproduce a stored
        float exactly.

        The nearest breakpoint inside the window wins. At the default tolerance
        that is the only one there, but a caller widening the window is snapping
        a measured position onto the model's, and means the closest.
        """
        if address in self._graph_nodes:
            return address
        if position_tol is None:
            position_tol = _POSITION_TOLERANCE
        elif not math.isfinite(position_tol) or position_tol < 0:
            raise ValueError(
                f"position_tol must be a finite, non-negative number, got {position_tol!r}."
            )
        if not _is_breakpoint(address):
            return None
        reach_id, position = address
        known = self._positions.get(reach_id, [])
        # Only the two positions either side of the one asked for can be nearest;
        # of two equally near, the lower wins.
        i = bisect.bisect_left(known, position)
        nearest = min(known[max(i - 1, 0) : i + 1], key=lambda d: abs(d - position), default=None)
        if nearest is None or abs(nearest - position) > position_tol:
            return None
        return (reach_id, nearest)

    def describe_miss(self, address: Address, limit: int = 5) -> str:
        """Say what the network holds nearest to an address it does not.

        Names a few likely candidates rather than every name in the network.
        """
        if _is_breakpoint(address):
            reach_id, position = address
            known = self._positions.get(reach_id, [])
            if reach_id not in self._reaches:
                return self._describe_missing_reach(reach_id, limit)
            if not known:
                return f"reach {reach_id!r} has no breakpoints"
            # Past the last breakpoint of a reach of unknown length there is no
            # end position to match, and widening the window would only snap
            # onto a breakpoint nearer the start.
            if self._reaches[reach_id].length is None and position > known[-1]:
                return (
                    f"reach {reach_id!r} has no known length, so a position past its last "
                    f"breakpoint ({known[-1]:g}) cannot be matched, however wide position_tol "
                    "is; a length can come from Network.open's companions"
                )
            nearest = sorted(sorted(known, key=lambda d: abs(d - position))[:limit])
            listed = ", ".join(format(d, "g") for d in nearest)
            return (
                f"nearest positions on reach {reach_id!r}: {listed} "
                "(position_tol= widens the match)"
            )

        names = [key for key in self._graph_nodes if not _is_breakpoint(key)]
        close = get_close_matches(address, names, n=limit)
        if close:
            return "did you mean " + ", ".join(repr(name) for name in close) + "?"
        return f"the network has {len(names)} nodes, none named {address!r}"

    def _describe_missing_reach(self, reach_id: str, limit: int) -> str:
        # A structure reach keeps the type prefix its file gives it
        # ("Weir:119w1"), which a caller holding the bare structure id, as
        # Res1D.structures gives it, has not typed.
        close = [known for known in self._reaches if known.partition(":")[2] == reach_id]
        close = close or get_close_matches(reach_id, list(self._reaches), n=limit)
        if close:
            listed = ", ".join(repr(known) for known in close[:limit])
            return f"the network has no reach {reach_id!r}; did you mean {listed}?"
        return f"the network has no reach {reach_id!r}"
