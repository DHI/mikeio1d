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
    ResultCatchment,
    ResultReach,
    ResultReaches,
)


class Res1DNodeType(Enum):
    """Type of the original network element."""

    NODE = 1
    GRIDPOINT = 2


class NetworkNode:
    """Node in the simplified network."""

    def __init__(
        self,
        element: ResultNode | ResultGridPoint,
    ):
        self._validate_element_type(element)

        self.id = self._generate_alias(element)
        self._quantities = element.quantities
        self.data = self._build_node_data(element)

    def _validate_element_type(self, element: ResultNode | ResultGridPoint):
        if isinstance(element, ResultNode):
            self._node_type = Res1DNodeType.NODE
        elif isinstance(element, ResultGridPoint):
            self._node_type = Res1DNodeType.GRIDPOINT
        else:
            raise ValueError("Invalid element type")

    def _generate_alias(self, element: ResultNode | ResultGridPoint) -> str:
        if self.type == Res1DNodeType.GRIDPOINT:
            return f"{"gridpoint"}-{element.reach_name}-{round(element.chainage, 3)}"
        else:
            return f"{"node"}-{element.id}"

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


class NetworkEdge:
    """Generic edge class."""

    def __init__(self, edge: Any):
        if isinstance(edge, ResultReach):
            self._parse_from_res1d(edge)
        else:
            raise NotImplementedError("Only Res1D formats are supported")

    def _parse_from_res1d(self, edge: ResultReach):
        self._start = edge.start_node
        self._end = edge.end_node
        self._id = edge.name
        self._length = edge.length

    @property
    def start(self) -> str:
        """Id of the starting node of the edge.

        Returns
        -------
        str
        """
        return self._start

    @property
    def end(self) -> str:
        """Id of the ending node of the edge.

        Returns
        -------
        str
        """
        return self._end

    @property
    def id(self) -> str:
        """Id of the edge.

        Returns
        -------
        str
        """
        return self._id

    @property
    def length(self) -> float:
        # TODO: handle units
        """Length of the edge.

        Returns
        -------
        str
        """
        return self._length


class NetworkEdgeCollection:
    """Collection of network edges."""

    def __init__(self, edges: List[NetworkEdge] | ResultReaches):
        if isinstance(edges, ResultReaches):
            edges = [NetworkEdge(edge) for edge in edges.values()]
        self._dict = {edge.id: edge for edge in edges}

    def __getitem__(self, key: str) -> NetworkEdge:
        """Get edge by ID like a dictionary."""
        return self._dict[key]

    def __contains__(self, key: str) -> bool:
        """Check if edge ID exists in the collection."""
        return key in self._dict


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


class Res1DMapper:
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

    def _parse_nodes_and_edges(res: Any) -> Tuple[List[NetworkNode], List[NetworkEdge]]:
        if isinstance(res, Res1D):
            nodes = res.nodes
            edges = NetworkEdgeCollection(res.reaches)
            return nodes, edges
        else:
            raise NotImplementedError("Only Res1D formats are supported.")

    def _initialize_graph(self) -> nx.Graph:
        g0 = nx.Graph()
        for edge in self._edges:
            g0.add_edge(edge.start, edge.end, name=edge.id, length=edge.length)
        return g0.copy()

    def _validate_priority(self):
        valid_keys = {"edges", "inclusions"}
        priority_keys = set(self.priority.keys())
        if not priority_keys.issubset(valid_keys):
            raise ValueError(f"Invalid keys in priority, they must be one of {valid_keys}")
        if "inclusions" not in self.priority:
            self.priority["inclusions"] = {}

    def _choose_element(self, elements: List[ResultNode | ResultGridPoint]) -> NetworkNode:
        # TODO: refresh, can catchment be an overlapping element?
        # TODO: prioritize by quantity

        if len(elements) == 0:
            raise ValueError("elements list should contain at least one element.")

        if len(elements) == 1:
            # Only one element was found, which is directly passed to the network
            element = elements[0]
        else:
            # Multiple overlapping elements were found, so we check priority
            node_elements = [element for element in elements if isinstance(element, ResultNode)]

            priority_elements = []
            for element in elements:
                if isinstance(element, ResultGridPoint) and (
                    element.reach_name in self.priority["edges"]
                ):
                    priority_elements.append(element)
                elif isinstance(element, ResultCatchment):
                    raise NotImplementedError("'Catchments' are still not supported")

            if len(priority_elements) == 0:
                if len(node_elements) == 0:
                    raise ValueError("Neither node nor prioritized gridpoints were found.")
                elif len(node_elements) > 1:
                    raise ValueError("There cannot be more than one 'ResultNode'.")
                else:
                    element = node_elements[0]
            elif len(priority_elements) > 1:
                raise ValueError("Multiple elements were prioritized in this intersection.")
            else:
                element = priority_elements[0]

        return NetworkNode(element)

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

    def _find_overlapping_elements(
        self, node: ResultNode, g0: nx.Graph
    ) -> List[ResultNode | ResultGridPoint]:
        def get_touching_reaches() -> List[ResultReach]:
            return [self._edges[data["name"]] for _, _, data in g0.edges(node.id, data=True)]

        touching_reaches = get_touching_reaches()
        # Finding elements that are overlapping (node and gridpoint ends)
        gridpoints = []
        for reach in touching_reaches:
            if reach.start_node == node.id:
                gridpoints.append(reach.gridpoints[0])
            elif reach.end_node == node.id:
                gridpoints.append(reach.gridpoints[-1])
        return [node] + gridpoints

    def _prioritize_graph_elements(self, g0: nx.Graph) -> nx.Graph:
        alias_map = {}
        for node_id in g0.nodes:
            node = self._edges[node_id]
            elements = self._find_overlapping_elements(node, g0)
            element = self._choose_element(elements)
            alias_map[node_id] = element.id
            g0.nodes[node_id]["data"] = element.data
        return nx.relabel_nodes(g0, alias_map, copy=True)

    def _update_graph(self, g0: nx.Graph) -> nx.Graph:
        g0 = self._prioritize_graph_elements(g0)
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
