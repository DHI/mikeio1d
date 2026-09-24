"""Describe a network's loader output as a plain, comparable dictionary.

The point of a snapshot is to pin down what the loader produces today, so the
same behaviour can be demanded of the module once it lives in mikeio1d (ADR-013).
Two constraints follow from that, and both matter:

* nothing here imports modelskill. :func:`describe` takes a network and returns
  built-in types, so this file moves to another repository with only its
  fixture-loading callers changed.
* nothing here records *how* the network was built. No constructor name reaches
  the output, so a snapshot taken through one entry point still matches when the
  entry points are reshaped.

Floats are rounded on the way in, since a snapshot is meant to be read in a
diff. Comparison is left to the caller, which can afford a tolerance the file
format cannot express.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np

_DECIMALS = 6
"""Rounding applied to every float. Well below any change worth noticing."""


def _num(value: Any) -> float | int | None:
    """Round a number for storage, mapping NaN and None alike to None.

    Parameters
    ----------
    value : float, int or None
        The number as the network reported it.

    Returns
    -------
    float, int or None
        None where there is no value, so the snapshot stays strict JSON rather
        than relying on a NaN literal.
    """
    if value is None:
        return None
    if isinstance(value, bool):
        return int(value)
    value = float(value)
    if math.isnan(value):
        return None
    return round(value, _DECIMALS)


def _alias_key(alias: Any) -> str:
    """Render a node or breakpoint alias as a string, for use as a JSON key.

    Parameters
    ----------
    alias : str or tuple
        A node id, or a ``(reach, distance)`` breakpoint pair.

    Returns
    -------
    str
        ``node:<id>`` or ``bp:<reach>@<distance>``. The prefix keeps the two
        spaces apart, so a node named like a reach cannot collide with a
        breakpoint on it.
    """
    if isinstance(alias, tuple):
        reach, distance = alias
        rendered = "None" if distance is None else repr(_num(distance))
        return f"bp:{reach}@{rendered}"
    return f"node:{alias}"


def _digest(series: Any) -> dict[str, Any]:
    """Summarise a timeseries column, in place of storing its values.

    Parameters
    ----------
    series : pandas.Series
        One location's values for one quantity.

    Returns
    -------
    dict
        Count, missing count and five statistics. Enough that a change in any
        value moves at least one of them, and small enough to read.
    """
    values = np.asarray(series.to_numpy(dtype="float64"))
    finite = values[~np.isnan(values)]
    return {
        "n": int(values.size),
        "n_nan": int(values.size - finite.size),
        "first": _num(values[0]) if values.size else None,
        "last": _num(values[-1]) if values.size else None,
        "min": _num(finite.min()) if finite.size else None,
        "max": _num(finite.max()) if finite.size else None,
        "sum": _num(finite.sum()) if finite.size else None,
    }


def _carried(df: Any) -> dict[int, list[str]]:
    """Group a network's dataframe columns by the graph node they belong to.

    Parameters
    ----------
    df : pandas.DataFrame
        What ``to_dataframe()`` returned, with ``(node, quantity)`` columns.

    Returns
    -------
    dict of int to list of str
        Sorted quantity names per graph node. A node carrying nothing is absent.
    """
    carried: dict[int, list[str]] = {}
    for node, quantity in df.columns:
        carried.setdefault(int(node), []).append(str(quantity))
    return {node: sorted(quantities) for node, quantities in carried.items()}


def _describe_graph(network: Any, carried: dict[int, list[str]]) -> dict[str, Any]:
    """Describe the graph: its edges, and what each node carries.

    Parameters
    ----------
    network : Network
        The network to describe.
    carried : dict of int to list of str
        What each graph node carries, from :func:`_carried`.

    Returns
    -------
    dict
        Edges keyed by alias rather than by the integer label, so an edge stays
        recognisable even if the numbering were to change, plus the alias map
        itself so that the numbering is pinned too.
    """
    graph = network.graph
    aliases = {node: graph.nodes[node]["alias"] for node in graph.nodes}

    edges = []
    for u, v, attrs in graph.edges(data=True):
        ends = sorted((_alias_key(aliases[u]), _alias_key(aliases[v])))
        edges.append([*ends, _num(attrs.get("length")), bool(attrs.get("boundary"))])
    edges.sort(key=lambda edge: (edge[0], edge[1], str(edge[2])))

    nodes = {_alias_key(aliases[node]): carried.get(int(node), "empty") for node in graph.nodes}

    return {
        "edges": edges,
        "nodes": nodes,
        "alias_map": {
            _alias_key(alias): int(node_id)
            for node_id, alias in network.graph.nodes(data="alias")
        },
    }


def _describe_reaches(network: Any, carried: dict[int, list[str]]) -> dict[str, Any]:
    """Describe every reach: its ends, its length and its breakpoints.

    Parameters
    ----------
    network : Network
        The network to describe.
    carried : dict of int to list of str
        What each graph node carries, from :func:`_carried`.

    Returns
    -------
    dict
        One entry per reach id.
    """
    by_alias = {alias: int(node) for node, alias in network.graph.nodes(data="alias")}
    described = {}
    for reach_id, reach in network.reaches.items():
        described[str(reach_id)] = {
            "start": str(reach.start.id),
            "end": str(reach.end.id),
            "length": _num(reach.length),
            "n_breakpoints": int(reach.n_breakpoints),
            "breakpoints": [
                {
                    "id": _alias_key(breakpoint.id),
                    "distance": _num(breakpoint.distance),
                    "quantities": carried.get(by_alias[breakpoint.id], []),
                }
                for breakpoint in reach.breakpoints
            ],
        }
    return described


def _describe_dataframe(df: Any) -> dict[str, Any]:
    """Describe the assembled dataframe, values included as digests.

    Parameters
    ----------
    df : pandas.DataFrame
        What ``to_dataframe()`` returned.

    Returns
    -------
    dict
        Shape, time span and a digest per ``(node, quantity)`` column. This is
        the numeric truth the move must not disturb.
    """
    index = df.index
    return {
        "shape": list(df.shape),
        "time": {
            "first": None if len(index) == 0 else str(index[0]),
            "last": None if len(index) == 0 else str(index[-1]),
            "n": int(len(index)),
        },
        "columns": {
            f"{node}|{quantity}": _digest(df[(node, quantity)]) for node, quantity in df.columns
        },
    }


def _describe_lookups(network: Any) -> dict[str, Any]:
    """Record how every location's name and graph integer correspond.

    Parameters
    ----------
    network : Network
        The network to describe.

    Returns
    -------
    dict
        ``find``: the integer ``resolve`` gives each address. ``endpoints``: the
        integer of each reach's start and end node. ``recall``: the name the
        graph labels each integer with. A breakpoint whose distance is unknown
        is absent from ``find``: no address names it, which is behaviour
        recorded under ``reaches`` instead.
    """
    found = {}
    for _, alias in network.graph.nodes(data="alias"):
        if isinstance(alias, tuple) and alias[1] is None:
            continue
        found[_alias_key(alias)] = int(network.resolve(alias)["node"])

    endpoints = {}
    for reach_id, reach in network.reaches.items():
        for where, node in (("start", reach.start), ("end", reach.end)):
            endpoints[f"{reach_id}@{where}"] = int(network.resolve(node.id)["node"])

    recalled = {}
    for node_id, alias in sorted(network.graph.nodes(data="alias")):
        if isinstance(alias, tuple):
            entry = {"reach": alias[0], "distance": _num(alias[1])}
        else:
            entry = {"node": alias}
        recalled[str(node_id)] = entry

    return {"find": found, "endpoints": endpoints, "recall": recalled}


def describe(network: Any) -> dict[str, Any]:
    """Describe everything a loader decided, as plain comparable data.

    Parameters
    ----------
    network : Network
        A loaded network. Nothing about how it was loaded is recorded.

    Returns
    -------
    dict
        Nested built-in types only, safe to serialise as strict JSON.

    Notes
    -----
    ``to_dataset()`` is deliberately absent. Its coordinates are due to change,
    while the values underneath it are pinned by the dataframe digests.
    """
    df = network.to_dataframe()
    carried = _carried(df)
    return {
        "counts": {
            "reaches": len(network.reaches),
            "graph_nodes": int(network.graph.number_of_nodes()),
            "graph_edges": int(network.graph.number_of_edges()),
        },
        "quantities": sorted(str(q) for q in network.quantities),
        "graph": _describe_graph(network, carried),
        "reaches": _describe_reaches(network, carried),
        "dataframe": _describe_dataframe(df),
        "lookups": _describe_lookups(network),
    }
