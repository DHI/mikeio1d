"""Match the names a model gave its locations to the graph's nodes.

A result file names a location the way the model did: a node id, or a reach and
a distance along it. This module holds the rule for when two distances mean the
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

# Tolerance for comparing along-reach chainage/distance values, in whatever
# distance unit the network uses. Two distances within it are the same place,
# which is what a tolerant lookup asks and what the graph builder asks of an
# edge whose ends coincide.
_CHAINAGE_TOLERANCE = 1e-3

Address = str | tuple[str, float]
"""A location under the name its model gave it.

A plain ``str`` is a node id. A ``(reach_id, distance)`` tuple is a break point.
Nothing is both, so the shape says which it is.
"""


def _is_break_point(address: Address) -> bool:
    """Whether an address names a break point rather than a node."""
    return isinstance(address, tuple)


class _Naming:
    """The addresses in a network, and their graph nodes, built once from a graph.

    Parameters
    ----------
    graph : nx.Graph
        The integer-labelled graph, each node carrying its ``address``.
    reaches : Mapping[str, NetworkReach]
        The network's reaches, by id, for telling a missing reach from a
        missing distance on one.
    """

    def __init__(self, graph: nx.Graph, reaches: Mapping[str, NetworkReach]):
        self._nodes: dict[Address, int] = {
            address: node for node, address in graph.nodes(data="address")
        }
        # Each reach's break point distances, ascending, for bisect.
        self._distances: dict[str, list[float]] = {}
        for address in self._nodes:
            if _is_break_point(address):
                self._distances.setdefault(address[0], []).append(address[1])
        for known in self._distances.values():
            known.sort()
        self._reaches = reaches

    @property
    def nodes(self) -> Mapping[Address, int]:
        """Every address in the network, mapped to its graph node."""
        return self._nodes

    def canonical(self, address: Address, *, distance_tol: float | None = None) -> Address | None:
        """Give the network's own spelling of an address, or None if there is no such place.

        An exact hit answers immediately. Failing that, a break point is matched
        on distance within ``distance_tol``, defaulting to
        :data:`_CHAINAGE_TOLERANCE`, so a caller need not reproduce a stored
        float exactly.

        The nearest break point inside the window wins. At the default tolerance
        that is the only one there, but a caller widening the window is snapping
        a measured distance onto the model's, and means the closest.
        """
        if address in self._nodes:
            return address
        if distance_tol is None:
            distance_tol = _CHAINAGE_TOLERANCE
        elif not math.isfinite(distance_tol) or distance_tol < 0:
            raise ValueError(
                f"distance_tol must be a finite, non-negative number, got {distance_tol!r}."
            )
        if not _is_break_point(address):
            return None
        reach_id, distance = address
        known = self._distances.get(reach_id, [])
        # Only the two distances either side of the one asked for can be nearest;
        # of two equally near, the lower wins.
        i = bisect.bisect_left(known, distance)
        nearest = min(known[max(i - 1, 0) : i + 1], key=lambda d: abs(d - distance), default=None)
        if nearest is None or abs(nearest - distance) > distance_tol:
            return None
        return (reach_id, nearest)

    def describe_miss(self, address: Address, limit: int = 5) -> str:
        """Say what the network holds nearest to an address it does not.

        Names a few likely candidates rather than every name in the network.
        """
        if _is_break_point(address):
            reach_id, distance = address
            known = self._distances.get(reach_id, [])
            if not known:
                if reach_id not in self._reaches:
                    return f"the network has no reach {reach_id!r}"
                return f"reach {reach_id!r} has no break points"
            nearest = sorted(sorted(known, key=lambda d: abs(d - distance))[:limit])
            listed = ", ".join(format(d, "g") for d in nearest)
            return (
                f"nearest distances on reach {reach_id!r}: {listed} "
                "(distance_tol= widens the match)"
            )

        names = [key for key in self._nodes if not _is_break_point(key)]
        close = get_close_matches(address, names, n=limit)
        if close:
            return "did you mean " + ", ".join(repr(name) for name in close) + "?"
        return f"the network has {len(names)} nodes, none named {address!r}"
