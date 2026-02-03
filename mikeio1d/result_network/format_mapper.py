from __future__ import annotations

from dataclasses import dataclass

import networkx as nx
import pandas as pd

from typing import Dict, List, Optional

from mikeio1d import Res1D
from mikeio1d.result_network import ResultNode, ResultGridPoint, ResultCatchment


class NetworkNode:
    """Network node in the simplified network."""

    def __init__(
        self,
        element: Optional[ResultNode | ResultGridPoint],
        *,
        # TODO: we might want to include all quantities in the element and then we can remove this argument
        quantity: Optional[str],
    ):
        self._ntype = type(element)
        valid_init = (quantity is not None) and (element is not None)
        self._empty_node = (quantity is None) and (element is None)
        if valid_init:
            self.id = self._generate_id(element)
            self.quantity = quantity
            self.series = self.get_pd_series(element)
        elif self._empty_node:
            self.id = None
            self.quantity = None
            self.series = None
        else:
            raise ValueError(
                "Invalid node init: either contains id, quantity and df or none of them."
            )

    @staticmethod
    def _generate_id(element: ResultNode | ResultGridPoint) -> str:
        if isinstance(element, ResultGridPoint):
            return f"{"gridpoint"}-{element.reach_name}-{round(element.chainage, 3)}"
        elif isinstance(element, ResultNode):
            return f"{"node"}-{element.id}"
        else:
            raise ValueError("Invalid element type.")

    @property
    def is_empty(self) -> bool:
        return self._empty_node

    def get_pd_series(self, element: ResultNode | ResultGridPoint) -> pd.Series:
        df = element.to_dataframe()
        relevant_columns = [col for col in df.columns if self.quantity in col]
        assert len(relevant_columns) == 1, "Multiple relevant columns were found!"
        col = relevant_columns[0]
        return df[col].copy()


class Res1DMapper:
    """Mapper class to transform Res1D to a general network coord system."""

    def __init__(self, res: Res1D, quantity: str, priority: Dict[str, List]):
        assert quantity in res.quantities, f"Network does not include quantity={quantity}"
        self.quantity = quantity

        self.priority = priority
        self.validate_priority()

        self._res1d = res
        self.graph = self._generate_graph()
        self._node_map = self._generate_node_map(self.graph)

        self._df = pd.concat({k: v["series"] for k, v in self.graph.nodes.items()}, axis=1)

    def validate_priority(self):
        assert True

    def validate_inclusions(self):
        assert True

    def get_overlapping_elements(self, node: ResultNode) -> List[ResultNode | ResultGridPoint]:
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
        elements = self.get_overlapping_elements(node)
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
                    element.reach_name in self.priority["edge"]
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

    def get_node(self, id: str) -> int:
        return self._node_map[id]

    def _initialize_graph(self) -> nx.Graph:
        graph = nx.Graph()
        n = 0
        for node in list(self._res1d.nodes.values()):
            element = self._prioritize_node(node)
            if not element.is_empty:
                graph.add_node(n, series=element.series, id=element.id)
                n += 1

        return graph

    @staticmethod
    def _generate_node_map(graph: nx.Graph) -> Dict[str, int]:
        return {v["id"]: k for k, v in graph.nodes.items()}

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
