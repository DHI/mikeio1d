"""FormatMapper class."""

from __future__ import annotations

import networkx as nx
import pandas as pd

from enum import Enum
from typing import Dict, List, Optional

from mikeio1d import Res1D
from mikeio1d.result_network import ResultNode, ResultGridPoint, ResultCatchment, ResultReach


class Res1DNodeType:
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


class Res1DMapper:
    """Mapper class to transform Res1D to a general network coord system."""

    def __init__(self, res: Res1D, priority: Dict[str, List]):
        self._res1d = res
        self.priority = priority
        self._validate_priority()

        self._g0 = self._initialize_graph()
        self._update_graph()
        self._df = self._build_node_dataframe()

    def _initialize_graph(self) -> nx.Graph:
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
        if element.id in self._g0.nodes:
            return element.id
        else:
            # When the element id does not correspond to any node and is not
            # a key in the alias map, it means that such element was never parsed.
            raise ValueError("Element is not present in the network.")

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

    def _prioritize_graph_elements(self):
        alias_map = {}
        for node_id in self._g0.nodes:
            node = self._res1d.nodes[node_id]
            elements = self._find_overlapping_elements(node)
            element = self._choose_element(elements)
            alias_map[node_id] = element.id
            self._g0.nodes[node_id]["data"] = element.data
        nx.relabel_nodes(self._g0, alias_map, copy=False)

    def _get_touching_reaches(self, node: ResultNode) -> List[ResultReach]:
        return [
            self._res1d.reaches[data["name"]] for _, _, data in self._g0.edges(node.id, data=True)
        ]

    def _update_graph(self) -> Dict[str, str]:
        self._prioritize_graph_elements()
        if "inclusions" in self.priority:
            self._add_inclusions()

    def _add_inclusions(self) -> Dict[str, str]:
        # Some measurements might be taken in the middle of an edge. In a Res1D
        # file that node is found as a gridpoint that has an associated chainage.
        # We select it and convert it into a node.
        for inclusion in self.priority["inclusions"]:
            edge_id = inclusion["edge"]
            distance = inclusion["distance"]
            reach = self._res1d.reaches[edge_id]

            start_node = NetworkNode(self._res1d.nodes[reach.start_node])
            end_node = NetworkNode(self._res1d.nodes[reach.end_node])

            edge_data = self._g0.get_edge_data(start_node.id, end_node.id)
            total_length = edge_data.get("length", 1)
            self._g0.remove_edge(start_node.id, end_node.id)

            element = NetworkNode(reach[distance])
            self._g0.add_node(element.id, data=element.data)
            self._g0.add_edge(start_node.id, element.id, length=distance)
            self._g0.add_edge(element.id, end_node.id, length=total_length - distance)

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
