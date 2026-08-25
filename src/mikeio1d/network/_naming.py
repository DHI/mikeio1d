"""Translate between the names a model gave a location and the graph's integers.

A result file names a location the way the model did: a node id, or a reach and
a distance along it. A graph needs one flat set of integers. This module holds
both directions of that translation, the rule for when two distances mean the
same place, and the reach lookup that resolves a reach's own ends.

:class:`~mikeio1d.network.Network` builds one of these from its graph and keeps
it for the lifetime of the network; :meth:`~mikeio1d.network.Network.find`,
:meth:`~mikeio1d.network.Network.recall` and
:meth:`~mikeio1d.network.Network.to_dataset` are all delegations to it.
"""

from __future__ import annotations

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


def _is_break_point(alias: Alias) -> bool:
    """Whether an alias names a break point rather than a node."""
    return isinstance(alias, tuple)


class _Naming:
    """Both directions of the translation, built once from a graph.

    Parameters
    ----------
    graph : nx.Graph
        The integer-labelled graph, each node carrying its ``alias``.
    reaches : Mapping[str, NetworkReach]
        The network's reaches, by id, for resolving a reach's own ends.
    """

    def __init__(self, graph: nx.Graph, reaches: Mapping[str, NetworkReach]):
        self._by_alias: dict[Alias, int] = {
            graph.nodes[node_id]["alias"]: node_id for node_id in graph.nodes()
        }
        # Both directions are kept, rather than one inverted on demand: recall()
        # and to_dataset() each want the reverse of the whole map, and building
        # it per call made every lookup cost a pass over the network.
        self._by_id: dict[int, Alias] = {
            node_id: alias for alias, node_id in self._by_alias.items()
        }
        self._reaches = reaches

    def __contains__(self, alias: Alias) -> bool:
        return alias in self._by_alias

    @property
    def aliases(self) -> Mapping[Alias, int]:
        """Every alias in the network, mapped to its graph integer."""
        return self._by_alias

    def id_of(self, alias: Alias) -> int | None:
        """Give the graph integer for an alias, or None if there is no such place.

        An exact hit answers immediately. Failing that, a break point is matched
        on distance within :data:`_CHAINAGE_TOLERANCE`, so a caller need not
        reproduce a stored float exactly.
        """
        if alias in self._by_alias:
            return self._by_alias[alias]
        if _is_break_point(alias):
            reach_id, distance = alias
            for key, node_id in self._by_alias.items():
                if (
                    _is_break_point(key)
                    and key[0] == reach_id
                    and key[1] is not None
                    and abs(key[1] - distance) <= _CHAINAGE_TOLERANCE
                ):
                    return node_id
        return None

    def endpoint(self, reach_id: str, which: str) -> str:
        """Resolve one end of a reach, named 'start' or 'end', to its node id.

        Raises
        ------
        KeyError
            If the network has no reach by that id.
        """
        if reach_id not in self._reaches:
            raise KeyError(f"Reach '{reach_id}' not found in the network.")
        reach = self._reaches[reach_id]
        return reach.start.id if which == "start" else reach.end.id

    def alias_of(self, node_id: int) -> Alias:
        """Give the name a graph integer's location had before it became one.

        Raises
        ------
        KeyError
            If the network has no node by that integer.
        """
        if node_id not in self._by_id:
            raise KeyError(f"Node ID {node_id} not found in the network.")
        return self._by_id[node_id]

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

        An error that lists every name in the network is unreadable on a real
        model - the ``network.res1d`` fixture has some fifteen thousand - so the
        few candidates a caller plausibly meant are named instead.
        """
        if _is_break_point(alias):
            reach_id, distance = alias
            known = [
                key[1]
                for key in self._by_alias
                if _is_break_point(key) and key[0] == reach_id and key[1] is not None
            ]
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
