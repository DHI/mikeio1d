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

        self._g0 = self._initialize_graph()
        self._alias_map = self._update_graph_with_alias()
        self._df = self._build_node_dataframe()

    def _initialize_graph(self) -> nx.Graph:
        # We create an initial graph to store the topology of the network
        g0 = nx.Graph()
        for reach in self._res1d.reaches.values():
            g0.add_edge(reach.start_node, reach.end_node, name=reach.name, length=reach.length)
        return g0.copy()

    def _build_node_dataframe(self) -> pd.DataFrame:
        df = pd.concat({k: v["data"] for k, v in self._g0.nodes.items()}, axis=1)
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

    def _choose_element(self, elements: List[ResultNode | ResultGridPoint]) -> NetworkNode:
        # TODO: refresh, can catchment be an overlapping element?
        # TODO: prioritize by quantity

        if len(elements) == 0:
            return NetworkNode()
        elif len(elements) == 1:
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
        if isinstance(element, ResultNode):
            alias = element.id
        elif isinstance(element, ResultGridPoint):
            alias = NetworkNode(element).alias
        else:
            raise ValueError("Invalid element type")
        try:
            return self._alias_map[alias]
        except KeyError:
            # If the alias is not found in the node map, the passed element was not included
            # in the simplified network. Likely due to prioritization.
            raise ValueError("Element was not found in simplified network.")

    def _find_overlapping_elements(self, node: ResultNode) -> List[ResultNode | ResultGridPoint]:
        touching_reaches = self._get_touching_reaches(node)
        # Finding elements that are overlapping (node and gridpoint ends)
        gridpoints = []
        for reach in touching_reaches:
            if reach.start_node == node.id:
                gridpoints.append(reach.gridpoints[0])
            elif reach.end_node == node.id:
                gridpoints.append(reach.gridpoints[-1])
        return [node] + gridpoints

    def _create_alias_map(self) -> Dict[str, str]:
        alias_map = {}
        for node_id in self._g0.nodes:
            node = self._res1d.nodes[node_id]
            elements = self._find_overlapping_elements(node)
            element = self._choose_element(elements)
            if not element.is_empty:
                alias_map[node_id] = element.alias
                self._g0.nodes[node_id]["data"] = element.data

        nx.relabel_nodes(self._g0, alias_map, copy=False)
        return alias_map

    def _get_touching_reaches(self, node: ResultNode) -> List[ResultReach]:
        return [
            self._res1d.reaches[data["name"]] for _, _, data in self._g0.edges(node.id, data=True)
        ]

    def _update_graph_with_alias(self) -> Dict[str, str]:
        alias_map = self._create_alias_map()
        if "inclusions" in self.priority:
            alias_map = self._add_inclusions(alias_map)

        return alias_map

    def _add_inclusions(self, alias_map: Dict[str, int]) -> Dict[str, str]:
        for inclusion in self.priority["inclusions"]:
            edge_id = inclusion["edge"]
            distance = inclusion["distance"]
            reach = self._res1d.reaches[edge_id]

            start_id = alias_map[reach.start_node]
            end_id = alias_map[reach.end_node]
            edge_data = self._g0.get_edge_data(start_id, end_id)
            total_length = edge_data.get("length", 1)
            self._g0.remove_edge(start_id, end_id)

            element = NetworkNode(reach[distance])
            self._g0.add_node(element.alias, data=element.data)
            self._g0.add_edge(start_id, element.alias, length=distance)
            self._g0.add_edge(element.alias, end_id, length=total_length - distance)
            alias_map[element.alias] = element.alias

        return alias_map

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
