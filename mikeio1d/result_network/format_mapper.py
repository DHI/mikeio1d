"""FormatMapper class."""

from __future__ import annotations

from dataclasses import dataclass

import networkx as nx
import pandas as pd

from typing import Dict, List, Optional

from mikeio1d import Res1D
from mikeio1d.result_network import ResultNode, ResultGridPoint, ResultCatchment


class NetworkNode:
    """Node in the simplified network."""

    def __init__(
        self,
        element: Optional[ResultNode | ResultGridPoint],
        *,
        quantity: Optional[str],
    ):
        self._empty_node = element is None
        if self._empty_node:
            self.alias = None
            self.quantities = None
            self.data = None
        else:
            self.alias = self._generate_alias(element)
            self.quantities = element.quantities
            self.data = self._build_node_data(element, quantity)

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

    def _build_node_data(
        self, element: ResultNode | ResultGridPoint, quantity: Optional[str]
    ) -> pd.DataFrame:
        df = element.to_dataframe()
        renamer_dict = {}
        for quantity in self.quantities:
            relevant_columns = [col for col in df.columns if quantity in col]
            assert len(relevant_columns) == 1, "There must be exactly one column matching quantity"
            renamer_dict[relevant_columns[0]] = quantity
        df = df.rename(columns=renamer_dict)
        if quantity is not None:
            df = df[[quantity]].copy()
        return df.copy()


class Res1DMapper:
    """Mapper class to transform Res1D to a general network coord system."""

    def __init__(self, res: Res1D, quantity: str, priority: Dict[str, List]):
        assert quantity in res.quantities, f"Network does not include quantity={quantity}"
        self._res1d = res
        self.quantity = quantity
        self.priority = priority
        self._validate_priority()
        self.graph = self._generate_graph()
        self._node_map = self._generate_node_map(self.graph)

        self._df = pd.concat({k: v["series"] for k, v in self.graph.nodes.items()}, axis=1)

    def _validate_priority(self):
        valid_keys = {"edges", "nodes", "inclusions"}
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
        return [
            element
            for element in elements
            if (element is not None) and (self.quantity in element.quantities)
        ]

    def _prioritize_node(self, node: ResultNode) -> NetworkNode:
        # TODO: refresh, can catchment be an overlapping element?
        elements = self._get_overlapping_elements(node)
        if len(elements) == 0:
            return NetworkNode()
        elif len(elements) == 1:
            # Only one element was found, which is directly passed to the network
            element = elements[0]
            print(type(element))
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

        return NetworkNode(element, quantity=self.quantity)

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
        return self._node_map[alias]

    def _initialize_graph(self) -> nx.Graph:
        graph = nx.Graph()
        n = 0
        for node in list(self._res1d.nodes.values()):
            element = self._prioritize_node(node)
            if not element.is_empty:
                graph.add_node(n, series=element.data, alias=element.alias)
                n += 1

        return graph

    @staticmethod
    def _generate_node_map(graph: nx.Graph) -> Dict[str, int]:
        return {v["alias"]: k for k, v in graph.nodes.items()}

    def _fill_edges(self, graph: nx.Graph, node_map: Dict[str, int]) -> nx.Graph:
        for reach in list(self._res1d.reaches.values()):
            try:
                graph.add_edge(node_map[reach.start_node], node_map[reach.end_node])
            except KeyError:
                pass

        return graph

    def _generate_graph(self) -> nx.Graph:
        graph = self._initialize_graph()
        node_map = self._generate_node_map(graph)
        graph = self._fill_edges(graph, node_map)

        return graph

    @property
    def as_df(self) -> pd.DataFrame:
        """Dataframe using new node ids as column names.

        Returns
        -------
        pd.DataFrame
            Timeseries contained in graph nodes
        """
        return self._df
