"""FormatMapper class."""

from __future__ import annotations

import networkx as nx
import pandas as pd

from enum import Enum
from typing import Dict, List, Tuple, Any

from mikeio1d import Res1D
from mikeio1d.result_network import (
    ResultNode,
    ResultGridPoint,
    ResultReach,
    ResultReaches,
    ResultNodes,
)


class Res1DNodeType(Enum):
    """Type of the original network element."""

    NODE = 1
    GRIDPOINT = 2
    CATCHMENT = 3


class NetworkNode:
    """Node in the simplified network."""

    def __init__(
        self,
        element: Any,
    ):
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
                "Invalid element type, only ResultNode or ResultGridPoint from Res1D are supported."
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

    def __init__(self, priority: Dict[str, List]):
        self.priority = priority
        self._validate_priority()

    def map_network(self, res: Res1D) -> GenericNetwork:
        """Return generic network object.

        Returns
        -------
        GenericNetwork
        """
        self._nodes, self._edges = self._parse_nodes_and_edges(res)
        g0 = self._initialize_graph()
        g0 = self._update_graph(g0)

        return GenericNetwork(g0)

    @staticmethod
    def _parse_nodes_and_edges(res: Any) -> Tuple[ResultNodes, ResultReaches]:
        if isinstance(res, Res1D):
            return res.nodes, res.reaches
        else:
            raise NotImplementedError("Only Res1D formats are supported.")

    def _initialize_graph(self) -> nx.Graph:
        g0 = nx.Graph()
        for edge in self._edges.values():
            start_node = NetworkNode(self._nodes[edge.start_node])
            end_node = NetworkNode(self._nodes[edge.end_node])
            g0.add_edge(start_node.id, end_node.id, name=edge.name, length=edge.length)
        return g0.copy()

    def _validate_priority(self):
        valid_keys = {"edges", "inclusions"}
        priority_keys = set(self.priority.keys())
        if not priority_keys.issubset(valid_keys):
            raise ValueError(f"Invalid keys in priority, they must be one of {valid_keys}")
        if "inclusions" not in self.priority:
            self.priority["inclusions"] = {}

    def get_node_id(self, element: ResultNode | ResultGridPoint) -> int:
        """Return the node id in the simplified network.

        Parameters
        ----------
        element : ResultNode | ResultGridPoint
            Element in the Res1D network

        Returns
        -------
        int
            Id in the simplified network
        """
        element = NetworkNode(element)
        return element.id

    def _prioritize_overlapping_element(self, node: NetworkNode, g0: nx.Graph) -> NetworkNode:
        adjacent_edges = [self._edges[data["name"]] for _, _, data in g0.edges(node.id, data=True)]
        relevant_edges = [edge for edge in adjacent_edges if edge.name in self.priority["edges"]]
        # Storing edge breaks if the edge is prioritized
        breaks = []
        for edge in relevant_edges:
            if edge.start_node == node.id:
                breaks.append(edge.gridpoints[0])
            elif edge.end_node == node.id:
                breaks.append(edge.gridpoints[-1])

        if len(breaks) == 0:
            return node
        elif len(breaks) == 1:
            return NetworkNode(breaks[0])
        else:
            raise ValueError("There cannot be multiple prioritized edges for the same node.")

    def _prioritize(self, g0: nx.Graph) -> nx.Graph:
        alias_map = {}
        for node in self._nodes.values():
            node = NetworkNode(node)
            element = self._prioritize_overlapping_element(node, g0)
            if element.id != node.id:  # An element has been prioritized
                alias_map[node.id] = element.id
            g0.nodes[node.id]["data"] = element.data
        # We rename based on the alias convention defined by NetworkNode class
        return nx.relabel_nodes(g0, alias_map, copy=True)

    def _update_graph(self, g0: nx.Graph) -> nx.Graph:
        g0 = self._prioritize(g0)
        g0 = self._add_inclusions(g0)
        return g0

    def _add_inclusions(self, g0: nx.Graph) -> nx.Graph:
        # Some measurements might be taken in the middle of an edge. In a Res1D
        # file that node is found as a gridpoint that has an associated chainage.
        # We select it and convert it into a node.
        for inclusion in self.priority["inclusions"]:
            edge_id = inclusion["edge"]
            distance = inclusion["distance"]
            edge = self._edges[edge_id]

            start_node = NetworkNode(self._nodes[edge.start_node])
            end_node = NetworkNode(self._nodes[edge.end_node])

            edge_data = g0.get_edge_data(start_node.id, end_node.id)
            total_length = edge_data.get("length", 1)
            g0.remove_edge(start_node.id, end_node.id)

            element = NetworkNode(edge[distance])
            g0.add_node(element.id, data=element.data)
            g0.add_edge(start_node.id, element.id, length=distance)
            g0.add_edge(element.id, end_node.id, length=total_length - distance)

        return g0.copy()
