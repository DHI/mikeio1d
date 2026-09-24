"""Match the names a model gave its locations, and label the graph's integers with them.

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
import numpy as np
import numpy.typing as npt

from ._types import NetworkReach

# Tolerance for comparing along-reach chainage/distance values, in whatever
# distance unit the network uses. Two distances within it are the same place,
# which is what a tolerant lookup asks and what the graph builder asks of an
# edge whose ends coincide.
_CHAINAGE_TOLERANCE = 1e-3

Alias = str | tuple[str, float | None]
"""A location under the name its model gave it.

A plain ``str`` is a node id. A ``(reach_id, distance)`` tuple is a break point,
whose ``distance`` is ``None`` where its position along the reach is genuinely
unknown. Nothing is both, so the shape says which it is.
"""

Address = str | tuple[str, float]
"""A location a caller can name.

The addressable part of :data:`Alias`. A break point whose distance is unknown -
an EPANET reach read without its ``.inp`` - has an alias and a graph node, but
nothing can ask for it by name.
"""


def _is_break_point(alias: Alias) -> bool:
    """Whether an alias names a break point rather than a node."""
    return isinstance(alias, tuple)


class _Naming:
    """The names in a network, and their graph integers, built once from a graph.

    Parameters
    ----------
    graph : nx.Graph
        The integer-labelled graph, each node carrying its ``alias``.
    reaches : Mapping[str, NetworkReach]
        The network's reaches, by id, for telling a missing reach from a
        missing distance on one.
    """

    def __init__(self, graph: nx.Graph, reaches: Mapping[str, NetworkReach]):
        self._by_alias: dict[Alias, int] = {
            graph.nodes[node_id]["alias"]: node_id for node_id in graph.nodes()
        }
        self._by_id: dict[int, Alias] = {
            node_id: alias for alias, node_id in self._by_alias.items()
        }
        # Each reach's known break point distances, ascending, for bisect.
        self._distances: dict[str, list[float]] = {}
        for alias in self._by_alias:
            if _is_break_point(alias) and alias[1] is not None:
                self._distances.setdefault(alias[0], []).append(alias[1])
        for known in self._distances.values():
            known.sort()
        self._reaches = reaches

    @property
    def aliases(self) -> Mapping[Alias, int]:
        """Every alias in the network, mapped to its graph integer."""
        return self._by_alias

    def canonical(self, address: Alias, *, tol: float | None = None) -> Alias | None:
        """Give the network's own spelling of an address, or None if there is no such place.

        An exact hit answers immediately. Failing that, a break point is matched
        on distance within ``tol``, defaulting to :data:`_CHAINAGE_TOLERANCE`, so
        a caller need not reproduce a stored float exactly.

        The nearest break point inside the window wins. At the default tolerance
        that is the only one there, but a caller widening the window is snapping
        a measured distance onto the model's, and means the closest.
        """
        if address in self._by_alias:
            return address
        if tol is None:
            tol = _CHAINAGE_TOLERANCE
        elif not math.isfinite(tol) or tol < 0:
            raise ValueError(
                f"A distance tolerance must be a finite, non-negative number, got {tol!r}."
            )
        if not _is_break_point(address) or address[1] is None:
            return None
        reach_id, distance = address
        known = self._distances.get(reach_id, [])
        # Only the two distances either side of the one asked for can be nearest;
        # of two equally near, the lower wins.
        i = bisect.bisect_left(known, distance)
        nearest = min(known[max(i - 1, 0) : i + 1], key=lambda d: abs(d - distance), default=None)
        if nearest is None or abs(nearest - distance) > tol:
            return None
        return (reach_id, nearest)

    def identity_coords(self, nodes: npt.ArrayLike) -> dict[str, tuple[str, np.ndarray]]:
        """Describe each node by the name it had before it became an integer.

        Parameters
        ----------
        nodes : array-like of int
            The integer ids to describe, in the order they appear.

        Returns
        -------
        dict
            ``name``, ``reach`` and ``distance`` arrays along the ``node``
            dimension. A node fills in ``name`` and leaves the other two empty; a
            breakpoint fills in ``reach`` and ``distance`` and leaves ``name``
            empty. Nothing carries both, so the empty half says which it is.
        """
        names, reaches, distances = [], [], []
        for node in np.asarray(nodes):
            alias = self._by_id[int(node)]
            if _is_break_point(alias):
                reach, distance = alias
                names.append("")
                reaches.append(reach)
                distances.append(np.nan if distance is None else distance)
            else:
                names.append(alias)
                reaches.append("")
                distances.append(np.nan)

        return {
            "name": ("node", np.array(names, dtype=str)),
            "reach": ("node", np.array(reaches, dtype=str)),
            "distance": ("node", np.array(distances, dtype=float)),
        }

    def describe_miss(self, alias: Alias, limit: int = 5) -> str:
        """Say what the network holds nearest to an alias it does not.

        Names a few likely candidates rather than every name in the network.
        """
        if _is_break_point(alias):
            reach_id, distance = alias
            known = self._distances.get(reach_id, [])
            if not known:
                if reach_id not in self._reaches:
                    return f"the network has no reach {reach_id!r}"
                return f"no break point of reach {reach_id!r} sits at a known distance"
            nearest = sorted(sorted(known, key=lambda d: abs(d - distance))[:limit])
            listed = ", ".join(format(d, "g") for d in nearest)
            return f"nearest distances on reach {reach_id!r}: {listed}"

        names = [key for key in self._by_alias if not _is_break_point(key)]
        close = get_close_matches(alias, names, n=limit)
        if close:
            return "did you mean " + ", ".join(repr(name) for name in close) + "?"
        return f"the network has {len(names)} nodes, none named {alias!r}"
