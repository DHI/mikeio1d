"""FormatMapper class."""

from __future__ import annotations

import networkx as nx
import pandas as pd

from typing import Dict, List, Optional, Tuple

from mikeio1d import Res1D
from mikeio1d.result_network import ResultNode, ResultGridPoint, ResultCatchment, ResultReach


class NetworkNode:
    """Node in the simplified network."""

    def __init__(
        self,
        element: Optional[ResultNode | ResultGridPoint],
    ):
        self._empty_node = element is None
        if self._empty_node:
            self.alias = None
            self.quantities = None
            self.data = None
        else:
            self.alias = self._generate_alias(element)
            self.quantities = element.quantities
            self.data = self._build_node_data(element)

    @staticmethod
    def _generate_alias(element: ResultNode | ResultGridPoint) -> str:
        if isinstance(element, ResultGridPoint):
            return f"{"gridpoint"}-{element.reach_name}-{round(element.chainage, 3)}"
        elif isinstance(element, ResultNode):
            return f"{"node"}-{element.id}"
        else:
            raise ValueError("Invalid element type.")

    @property
    def is_empty(self) -> bool:
        """Specifies if a node is empty.

        Returns
        -------
        bool
        """
        return self._empty_node

    def _build_node_data(self, element: ResultNode | ResultGridPoint) -> pd.DataFrame:
        df = element.to_dataframe()
        renamer_dict = {}
        for quantity in self.quantities:
            relevant_columns = [col for col in df.columns if quantity in col]
            assert len(relevant_columns) == 1, "There must be exactly one column matching quantity"
            renamer_dict[relevant_columns[0]] = quantity
        df = df.rename(columns=renamer_dict)
        return df.copy()


class Res1DMapper:
    """Mapper class to transform Res1D to a general network coord system."""

    def __init__(self, res: Res1D, priority: Dict[str, List]):
        self._res1d = res
        self.priority = priority
        self._validate_priority()
        self.graph, self._node_map = self._generate_graph_and_node_map()
        self._df = self._build_node_dataframe()

    def _build_node_dataframe(self) -> pd.DataFrame:
        df = pd.concat({k: v["data"] for k, v in self.graph.nodes.items()}, axis=1)
        df.columns = df.columns.set_names(["node", "quantity"])
        return df.copy()

    def _validate_priority(self):
        valid_keys = {"edges", "inclusions"}
        priority_keys = set(self.priority.keys())
        if not priority_keys.issubset(valid_keys):
            raise ValueError(f"Invalid keys in priority, they must be one of {valid_keys}")
        if "edges" in priority_keys:
            if not set(self.priority["edges"]).issubset(set(self._res1d.reaches.keys())):
                raise ValueError("'edges' must only include values found in reaches.")

    def _get_overlapping_elements(self, node: ResultNode) -> List[ResultNode | ResultGridPoint]:
        gridpoints = []
        for reach in list(self._res1d.reaches.values()):
            if reach.start_node == node.id:
                gridpoints.append(reach.gridpoints[0])
            elif reach.end_node == node.id:
                gridpoints.append(reach.gridpoints[-1])
        elements = [node] + gridpoints
        return [element for element in elements if element is not None]

    def _prioritize_node(self, node: ResultNode) -> NetworkNode:
        # TODO: refresh, can catchment be an overlapping element?
        # TODO: prioritize by quantity
        elements = self._get_overlapping_elements(node)
        if len(elements) == 0:
            return NetworkNode()
        elif len(elements) == 1:
            # Only one element was found, which is directly passed to the network
            element = elements[0]
        else:
            # Multiple elements were found, so we check priority
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
        alias = NetworkNode._generate_alias(element)
        try:
            return self._node_map[alias]
        except KeyError:
            # If the alias is not found in the node map, the passed element was not included
            # in the simplified network. Likely due to prioritization.
            raise ValueError("Element was not found in simplified network.")

    def _initialize_graph(self) -> nx.Graph:
        graph = nx.Graph()
        n = 0
        for node in list(self._res1d.nodes.values()):
            element = self._prioritize_node(node)
            if not element.is_empty:
                graph.add_node(n, data=element.data, alias=element.alias)
                n += 1

        return graph

    def _fill_edges(self, graph: nx.Graph, node_map: Dict[str, int]) -> nx.Graph:
        for reach in list(self._res1d.reaches.values()):
            try:
                start_id, end_id = self._get_reach_ends(reach, node_map)
                graph.add_edge(start_id, end_id, length=reach.length)
            except KeyError:
                pass

        return graph

    def _generate_graph_and_node_map(self) -> Tuple[nx.Graph, Dict[str, int]]:
        graph = self._initialize_graph()
        node_map = {v["alias"]: k for k, v in graph.nodes.items()}
        graph = self._fill_edges(graph, node_map)

        if "inclusions" in self.priority:
            graph, node_map = self._add_inclusions(graph, node_map)

        return graph, node_map

    def _add_inclusions(
        self, graph: nx.Graph, node_map: Dict[str, int]
    ) -> Tuple[nx.Graph, Dict[str, int]]:
        n = graph.number_of_nodes()
        for inclusion in self.priority["inclusions"]:
            edge_id = inclusion["edge"]
            distance = inclusion["distance"]
            reach = self._res1d.reaches[edge_id]
            element = NetworkNode(reach[distance])

            start_id, end_id = self._get_reach_ends(reach, node_map)

            edge_data = graph.get_edge_data(start_id, end_id)
            total_length = edge_data.get("length", 1)

            graph.remove_edge(start_id, end_id)
            graph.add_node(n, data=element.data, alias=element.alias)
            graph.add_edge(start_id, n, length=distance)
            graph.add_edge(n, end_id, length=total_length - distance)

            node_map[element.alias] = n
            n += 1

        return graph, node_map

    def _get_reach_ends(
        self, reach: ResultReach, node_map: Optional[Dict[str, int]] = None
    ) -> Tuple[str, str] | Tuple[int, int]:
        start_node = self._res1d.nodes[reach.start_node]
        end_node = self._res1d.nodes[reach.end_node]
        start_node_alias = NetworkNode._generate_alias(start_node)
        end_node_alias = NetworkNode._generate_alias(end_node)

        if node_map is None:
            # Returning aliased (using Res1D nomenclature)
            return start_node_alias, end_node_alias
        else:
            # Returning new ids (int)
            return node_map[start_node_alias], node_map[end_node_alias]

    @property
    def as_df(self) -> pd.DataFrame:
        """Dataframe using new node ids as column names.

        Returns
        -------
        pd.DataFrame
            Timeseries contained in graph nodes
        """
        return self._df
