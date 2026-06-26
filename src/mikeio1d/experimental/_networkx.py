from __future__ import annotations

from .. import Res1D
from typing import Literal, TYPE_CHECKING

if TYPE_CHECKING:
    import networkx as nx


def to_networkx(
    res: Res1D,
    graph_type: Literal["MultiDiGraph", "DiGraph", "MultiGraph", "Graph"] = "MultiDiGraph",
) -> nx.Graph:
    """Convert a Res1D object to a networkx Graph.

    Nodes become nodes, reaches become edges. Gridpoints ignored.

    Parameters
    ----------
    res : Res1D
        The Res1D object
    graph_type : {"MultiDiGraph", "DiGraph", "MultiGraph", "Graph"}, optional
        The type of networkx graph to return. Defaults to "MultiDiGraph".

    Returns
    -------
    nx.Graph / nx.DiGraph / nx.MultiGraph / nx.MultiDiGraph
        The networkx Graph object.

    Examples
    --------
    >>> from mikeio1d.experimental import to_networkx
    >>> G = to_networkx(res, graph_type="MultiDiGraph")
    """
    import networkx as nx

    if graph_type == "MultiDiGraph":
        G = nx.MultiDiGraph()
    elif graph_type == "DiGraph":
        G = nx.DiGraph()
    elif graph_type == "MultiGraph":
        G = nx.MultiGraph()
    elif graph_type == "Graph":
        G = nx.Graph()
    else:
        raise ValueError(f"Unsupported graph_type: {graph_type!r}")

    for reach in res.reaches.values():
        start, end = reach.start_node, reach.end_node
        G.add_edge(res.nodes[start], res.nodes[end], reach=reach)
    return G
