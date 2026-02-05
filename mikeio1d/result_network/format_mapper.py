"""FormatMapper class."""

from __future__ import annotations

import networkx as nx
import pandas as pd

from pathlib import Path
from enum import Enum
from typing import Dict, List, Tuple, Any, Iterator

from mikeio1d import Res1D
from mikeio1d.result_network import (
    ResultNode,
    ResultGridPoint,
    ResultReach,
    ResultNodes,
)


class NetworkBackend(Enum):
    """Backend of network."""

    RES1D = 1
    EPANET = 2


class Res1DNodeType(Enum):
    """Type of the original network element."""

    NODE = 1
    GRIDPOINT = 2
    CATCHMENT = 3


class NetworkNode:
    """Node in the simplified network."""

    def __init__(self, element: Any):
        if isinstance(element, (ResultNode, ResultGridPoint)):
            if isinstance(element, ResultNode):
                self._node_type = Res1DNodeType.NODE
            if isinstance(element, ResultGridPoint):
                self._node_type = Res1DNodeType.GRIDPOINT

            self._id = self._generate_alias(element)
            self._quantities = element.quantities
            self._data = self._build_node_data(element)
        else:
            raise NotImplementedError(
                f"Invalid element type {type(element)}, only ResultNode or ResultGridPoint from Res1D are supported."
            )

    def _generate_alias(self, element: ResultNode | ResultGridPoint) -> str:
        if isinstance(element, ResultGridPoint):
            return f"break@reach-{element.reach_name}-{round(element.chainage, 3)}"
        else:
            return f"node-{element.id}"

    def _build_node_data(self, element: ResultNode | ResultGridPoint) -> pd.DataFrame:
        df = element.to_dataframe()
        renamer_dict = {}
        for quantity in self.quantities:
            relevant_columns = [col for col in df.columns if quantity in col]
            assert len(relevant_columns) == 1, "There must be exactly one column matching quantity"
            renamer_dict[relevant_columns[0]] = quantity
        df = df.rename(columns=renamer_dict)
        return df.copy()

    @property
    def quantities(self) -> List[str]:
        """Quantities that are present in the node.

        Returns
        -------
        List[str]
        """
        return self._quantities

    @property
    def type(self) -> Res1DNodeType:
        """Type of the initial Res1D element."""
        return self._node_type

    @property
    def id(self) -> str:
        """Id of the node.

        Returns
        -------
        str
        """
        return self._id

    @property
    def data(self) -> pd.DataFrame:
        """Data in the node.

        Returns
        -------
        DataFrame
        """
        return self._data


class NodeCollection:
    """Collection of nodes."""

    def __init__(self, network: Any, backend: NetworkBackend):
        if backend == NetworkBackend.RES1D:
            node_dict = {node_id: NetworkNode(node) for node_id, node in network.nodes.items()}
        else:
            raise ValueError(f"Invalid backend {backend.name} for network of type {type(network)}")

        self._dict = node_dict

    def __getitem__(self, key: str) -> NetworkNode:
        """Get network node."""
        return self._dict[key]

    def __contains__(self, key: str) -> bool:
        """Check if edge ID exists in the collection."""
        return key in self._dict

    def keys(self) -> Iterator[str]:
        """Return edge IDs."""
        return self._dict.keys()

    def values(self) -> Iterator[NetworkNode]:
        """Return NetworkEdge objects."""
        return self._dict.values()

    def items(self) -> Iterator[Tuple[str, NetworkNode]]:
        """Return (id, edge) pairs."""
        return self._dict.items()

    def get(self, key: str, default=None) -> NetworkNode:
        """Get edge by ID with optional default value."""
        return self._dict.get(key, default)


class NetworkEdge:
    """Edge of a network."""

    def __init__(self, reach: ResultReach, nodes: ResultNodes):
        # TODO: currently this works only for Res1D files, it needs to be generalized
        self.id = reach.name
        self.start = NetworkNode(nodes[reach.start_node])
        self.end = NetworkNode(nodes[reach.end_node])
        self.length = reach.length
        # We only copy the breakpoints in the middle (the ends would need to be prioritized)
        self.breaks = [NetworkNode(point) for point in reach.gridpoints[1:-1]]
        # TODO: find a way to avoid loading the whole reach for getitem
        self._reach = reach

    def __getitem__(self, key: Any) -> NetworkNode:
        """Get network node."""
        return NetworkNode(self._reach[key])


class EdgeCollection:
    """Collection of nodes."""

    def __init__(self, network: Any, backend: NetworkBackend):
        if backend == NetworkBackend.RES1D:
            node_dict = {
                reach_id: NetworkEdge(reach, network.nodes)
                for reach_id, reach in network.reaches.items()
            }
        else:
            raise ValueError(f"Invalid backend {backend.name} for network of type {type(network)}")

        self._dict = node_dict

    def __getitem__(self, key: str) -> NetworkEdge:
        """Get network node."""
        return self._dict[key]

    def __contains__(self, key: str) -> bool:
        """Check if edge ID exists in the collection."""
        return key in self._dict

    def keys(self) -> Iterator[str]:
        """Return edge IDs."""
        return self._dict.keys()

    def values(self) -> Iterator[NetworkEdge]:
        """Return NetworkEdge objects."""
        return self._dict.values()

    def items(self) -> Iterator[Tuple[str, NetworkEdge]]:
        """Return (id, edge) pairs."""
        return self._dict.items()

    def get(self, key: str, default=None) -> NetworkEdge:
        """Get edge by ID with optional default value."""
        return self._dict.get(key, default)


class GenericNetwork:
    """Generic network structure."""

    def __init__(self, graph: nx.Graph):
        self._graph = graph.copy()
        self._df = self._build_node_dataframe()

    def _build_node_dataframe(self) -> pd.DataFrame:
        df = pd.concat({k: v["data"] for k, v in self._graph.nodes.items()}, axis=1)
        df.columns = df.columns.set_names(["node", "quantity"])
        return df.copy()

    @property
    def as_graph(self) -> nx.Graph:
        """Graph of the network."""
        return self._graph

    @property
    def as_df(self) -> pd.DataFrame:
        """Dataframe using new node ids as column names.

        Returns
        -------
        pd.DataFrame
            Timeseries contained in graph nodes
        """
        return self._df

    @property
    def quantities(self) -> List[str]:
        """Quantities present in data.

        Returns
        -------
        List[str]
            List of quantities
        """
        return list(self.as_df.columns.get_level_values(1).unique())


class NetworkMapper:
    """Mapper class to transform Res1D to a general network coord system."""

    def __init__(self):
        pass

    def map_network(self, res: Any) -> GenericNetwork:
        """Return generic network object.

        Returns
        -------
        GenericNetwork
        """
        self._nodes, self._edges = self._parse_nodes_and_edges(res)
        g0 = self._initialize_graph()

        return GenericNetwork(g0)

    @staticmethod
    def _parse_nodes_and_edges(res: Any) -> Tuple[NodeCollection, EdgeCollection]:
        if isinstance(res, (str, Path)):
            path = Path(res)
            if path.suffix.lower() == ".res1d":
                res = Res1D(res)
            else:
                raise NotImplementedError(
                    f"Unsupported file extension '{path.suffix}'. Only .res1d files are supported."
                )

        if isinstance(res, Res1D):
            backend = NetworkBackend.RES1D
        else:
            raise NotImplementedError(
                f"Only Res1D can be parsed, and network is of type {type(res)}"
            )
        nodes = NodeCollection(res, backend=backend)
        edges = EdgeCollection(res, backend=backend)
        return nodes, edges

    def _initialize_graph(self) -> nx.Graph:
        g0 = nx.Graph()
        for edge in self._edges.values():
            edge_points = [edge.start] + edge.breaks + [edge.end]
            for i in range(len(edge_points) - 1):
                start_i, end_i = edge_points[i], edge_points[i + 1]
                g0.add_edge(start_i.id, end_i.id)
                g0.nodes[start_i.id]["data"] = start_i.data
                g0.nodes[end_i.id]["data"] = end_i.data

            # Including an overlap with the data inside the extremes inside the edge
            for side in [edge.start, edge.end]:
                if "overlap" in g0.nodes[side.id]:
                    g0.nodes[side.id]["overlap"][edge.id] = side.data
                else:
                    g0.nodes[side.id]["overlap"] = {edge.id: side.data}

        return g0.copy()

    def get_node_id(self, element: ResultNode | ResultGridPoint) -> str:
        """Return the node id in the simplified network.

        Parameters
        ----------
        element : ResultNode | ResultGridPoint
            Element in the Res1D network

        Returns
        -------
        str
            Id in the simplified network
        """
        element = NetworkNode(element)
        return element.id
