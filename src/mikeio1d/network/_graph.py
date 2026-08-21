"""Build the graph a network is made of, and read it back.

One reach becomes a chain of edges: start node, its breakpoints in order, end
node. An edge carries the distance between its ends where that is known, and a
``boundary`` flag where the two ends are the same place - a gridpoint promoted to
a breakpoint sits exactly at the reach end it belongs to.

Every edge length is a difference between two positions in one reach's own
frame, so an offset frame - a MIKE river reach reporting chainages along the
whole branch - cancels out.

Two reaches between the same pair of nodes - parallel pumps, a battery of
orifices - stay apart because each one's break points are keyed by its own id,
so each gets its own chain of graph nodes. A reach with no break points has only
the one start-to-end edge, which is why two of those between the same nodes are
refused rather than collapsed into one.
"""

from __future__ import annotations

from collections.abc import Sequence

import networkx as nx
import pandas as pd

from ._types import NetworkReach

# Tolerance for comparing along-reach chainage/distance values, in whatever
# distance unit the network uses. Shared between find()'s breakpoint lookup
# and _generate_graph's boundary-edge detection.
_CHAINAGE_TOLERANCE = 1e-3


def _generate_graph(reaches: Sequence[NetworkReach]) -> nx.Graph:
    g0 = nx.Graph()
    # Which reach claimed each node pair with a bare start-to-end edge. Every
    # other edge this builds has a break point key - a (reach_id, distance)
    # tuple - at one end at least, so no two reaches can land on it.
    lone_reach_by_pair: dict[frozenset[str], str] = {}
    for reach in reaches:
        # 1) Add start and end nodes
        for node in [reach.start, reach.end]:
            node_key = node.id
            if node_key not in g0.nodes:
                g0.add_node(node_key, data=node.data)

        # 2) Add edges connecting start/end nodes to their adjacent breakpoints
        start_key = reach.start.id
        end_key = reach.end.id
        if reach.n_breakpoints == 0:
            pair = frozenset((start_key, end_key))
            claimed_by = lone_reach_by_pair.get(pair)
            if claimed_by is not None:
                raise ValueError(
                    f"Reaches {claimed_by!r} and {reach.id!r} both run between nodes "
                    f"{start_key!r} and {end_key!r}, and neither has break points, so the "
                    "graph cannot keep them apart. Give each of them at least one break "
                    "point: a reach with break points gets its own chain of graph nodes, "
                    "which is how a result file's parallel pumps and orifices stay distinct."
                )
            lone_reach_by_pair[pair] = reach.id
            g0.add_edge(start_key, end_key, length=reach.length, boundary=False)
        else:
            bp_keys = [bp.id for bp in reach.breakpoints]
            for bp, bp_key in zip(reach.breakpoints, bp_keys):
                g0.add_node(bp_key, data=bp.data)

            # A breakpoint sitting where the reach itself starts (or, on the
            # other end, where it ends) is not an intermediate point - it is
            # geometrically the same location as start_key/end_key, one of
            # the reach's own gridpoints promoted to a breakpoint. Tag that
            # edge and clamp it to an exact 0.0: the two coordinates in each
            # difference are each derived from a different upstream source,
            # so floating-point noise could otherwise leave a spurious tiny
            # positive or negative edge weight where the true value is
            # analytically zero. A breakpoint's distance can also be
            # genuinely unknown (unrelated to whether the reach's own length
            # is known - a NetworkReach subclass makes no promise the two are
            # coupled), so both ends guard for None.
            leading_distance = reach.breakpoints[0].distance
            if leading_distance is None:
                leading_length = None
                leading_is_boundary = False
            else:
                leading_diff = leading_distance - reach.start_distance
                leading_is_boundary = abs(leading_diff) <= _CHAINAGE_TOLERANCE
                leading_length = 0.0 if leading_is_boundary else leading_diff
            g0.add_edge(
                start_key,
                bp_keys[0],
                length=leading_length,
                boundary=leading_is_boundary,
            )

            # Only the final segment needs the total length, through
            # end_distance. Break point distances are known even when the
            # total is not, so a reach without a length still gets real
            # lengths on every edge but this one.
            trailing_distance = reach.breakpoints[-1].distance
            end_distance = reach.end_distance
            if end_distance is None or trailing_distance is None:
                tail_length = None
                tail_is_boundary = False
            else:
                tail_diff = end_distance - trailing_distance
                tail_is_boundary = abs(tail_diff) <= _CHAINAGE_TOLERANCE
                tail_length = 0.0 if tail_is_boundary else tail_diff
            g0.add_edge(
                bp_keys[-1],
                end_key,
                length=tail_length,
                boundary=tail_is_boundary,
            )

        # 3) Connect consecutive intermediate breakpoints
        for i in range(reach.n_breakpoints - 1):
            current_ = reach.breakpoints[i]
            next_ = reach.breakpoints[i + 1]
            if current_.distance is None or next_.distance is None:
                length = None
            else:
                length = next_.distance - current_.distance
            g0.add_edge(
                current_.id,
                next_.id,
                length=length,
                boundary=False,
            )

    return nx.convert_node_labels_to_integers(g0, label_attribute="alias")


def _generate_alias_map(g: nx.Graph) -> dict[str | tuple[str, float], int]:
    return {g.nodes[id]["alias"]: id for id in g.nodes()}


def _build_dataframe(g: nx.Graph) -> pd.DataFrame:
    data_in_nodes = {
        k: v["data"] for k, v in g.nodes.items() if v["data"] is not None and not v["data"].empty
    }
    if len(data_in_nodes) == 0:
        columns = pd.MultiIndex.from_arrays([[], []], names=["node", "quantity"])
        return pd.DataFrame(index=pd.Index([], name="time"), columns=columns)
    df = pd.concat(data_in_nodes, axis=1)
    df.columns = df.columns.set_names(["node", "quantity"])
    df.index.name = "time"
    return df.copy()
