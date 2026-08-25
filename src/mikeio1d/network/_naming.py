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

import networkx as nx

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
