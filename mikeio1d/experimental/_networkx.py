from __future__ import annotations

import networkx as nx
from .. import Res1D


def to_networkx(res: Res1D, directed: bool = True) -> nx.Graph:
    """Convert a Res1D object to a networkx Graph.

    Nodes become nodes, reaches become edges. Gridpoints ignored.

    Parameters
    ----------
    res : Res1D
        The Res1D object
    directed : bool, optional
        If True, returns a DiGraph (default). If False, returns an undirected Graph.

    Returns
    -------
    nx.Graph or nx.DiGraph
        The networkx Graph object.

    Examples
    --------
    Convert a mikeio1d.Res1D object into a networkx Graph (or DiGraph)

    >>> from mikeio1d.experimental import to_networkx
    >>> G = to_networkx(res, directed=True)

    Get dataframe of water level for all nodes within depth 3 of a particular node.

    >>> node = res.nodes['1']
    >>> for n in nx.bfs_tree(G, node, depth_limit=3).nodes:
    >>>     n.WaterLevel.add()
    >>> df = res.read()
    """
    G = nx.DiGraph() if directed else nx.Graph()
    for reach in res.reaches.values():
        start, end = reach.start_node, reach.end_node
        G.add_edge(res.nodes[start], res.nodes[end], reach=reach)
    return G
