from dataclasses import dataclass

import pandas as pd
import networkx as nx
import xarray as xr

from typing import Any, Protocol


class NetworkNodeIdGenerator(Protocol):
    """Bidirectional mapping between network coordinates and string IDs.

    Handles conversion from network element coordinates (node ID or edge + distance)
    to unique string identifiers and vice versa.
    """

    def generate(self, node: str | int | None = None, **kwargs) -> str: ...

    def parse(self, node_id: str) -> dict[str, Any]: ...


class NetworkNode(Protocol):
    """Node in the simplified network."""

    @property
    def id(self) -> str: ...

    @property
    def data(self) -> pd.DataFrame: ...

    @property
    def boundary(self) -> dict[str, Any]: ...

    @property
    def quantities(self) -> list[str]:
        return list(self.data.columns)


class EdgeBreakPoint(Protocol):
    """Edge break point."""

    @property
    def id(self) -> str: ...

    @property
    def data(self) -> pd.DataFrame: ...

    @property
    def distance(self) -> float: ...

    @property
    def quantities(self) -> list[str]:
        return list(self.data.columns)


class NetworkEdge(Protocol):
    """Edge of a network."""

    @property
    def id(self) -> str: ...

    @property
    def start(self) -> NetworkNode: ...

    @property
    def end(self) -> NetworkNode: ...

    @property
    def length(self) -> float: ...

    @property
    def breakpoints(self) -> list[EdgeBreakPoint]: ...

    @property
    def n_breakpoints(self) -> int:
        """Number of break points in the edge."""
        return len(self.breakpoints)


class GenericNetwork:
    """Generic network structure."""

    def __init__(self, graph: nx.Graph):
        self._graph = graph.copy()
        self._df = self._build_dataframe()

    def _build_dataframe(self) -> pd.DataFrame:
        df = pd.concat({k: v["data"] for k, v in self._graph.nodes.items()}, axis=1)
        df.columns = df.columns.set_names(["node", "quantity"])
        df.index.name = "time"
        return df.copy()

    def to_dataframe(self, sel: str | None = None) -> pd.DataFrame:
        """Dataframe using node ids as column names.

        It will be multiindex unless 'sel' is passed.

        Parameters
        ----------
        sel : Optional[str], optional
            Quantity to select, by default None

        Returns
        -------
        pd.DataFrame
            Timeseries contained in graph nodes
        """
        df = self._df.copy()
        if sel is None:
            return df
        else:
            df.attrs["quantity"] = sel
            return df.reorder_levels(["quantity", "node"], axis=1).loc[:, sel]

    def to_dataset(self) -> xr.Dataset:
        """Dataset using node ids as coords.

        Returns
        -------
        xr.Dataset
            Timeseries contained in graph nodes
        """
        df = self.to_dataframe()
        df = df.reorder_levels(["quantity", "node"], axis=1).melt(ignore_index=False)

        duplicate_check = df.reset_index().duplicated()
        if duplicate_check.any():
            raise ValueError("Duplicated values found")

        df = df.pivot_table(
            index=["time", "node"],
            columns="quantity",
            values="value",
            aggfunc="first",
        )
        return df.to_xarray()

    @property
    def graph(self) -> nx.Graph:
        """Graph of the network."""
        return self._graph

    @property
    def quantities(self) -> list[str]:
        """Quantities present in data.

        Returns
        -------
        List[str]
            List of quantities
        """
        return list(self.to_dataframe().columns.get_level_values(1).unique())


class NetworkMapper:
    """Mapper class to transform Res1D to a general network coord system."""

    def __init__(self, edges_dict: dict[str, NetworkEdge], id_generator: NetworkNodeIdGenerator):
        self._alias_map: dict[int, str] = {}
        # We include id_generator because we need a way to generate unique ids
        # of elements with arbitrary architecture. For instance, here we might pass
        # a function that depends on 'node' and 'reach' from res1d
        self._id_generator = id_generator
        self._edges = edges_dict

    def map_network(self) -> GenericNetwork:
        """Return generic network object.

        Returns
        -------
        GenericNetwork
        """
        g0 = self._initialize_graph()
        self._alias_map = {g0.nodes[id]["alias"]: id for id in g0.nodes()}

        return GenericNetwork(g0)

    def _initialize_graph(self) -> nx.Graph:
        g0 = nx.Graph()
        for edge in self._edges.values():
            # 1) Add start and end nodes
            for node in [edge.start, edge.end]:
                if node.id in g0.nodes:
                    g0.nodes[node.id]["boundary"].update(node.boundary)
                else:
                    g0.add_node(
                        node.id,
                        data=node.data,
                        boundary=node.boundary,
                    )

            # 2) Add edges connecting start/end nodes to their adjacent breakpoints
            if edge.n_breakpoints == 0:
                g0.add_edge(edge.start.id, edge.end.id, length=edge.length)
            else:
                for breakpoint in edge.breakpoints:
                    g0.add_node(breakpoint.id, data=breakpoint.data)

                g0.add_edge(
                    edge.start.id, edge.breakpoints[0].id, length=edge.breakpoints[0].distance
                )

                g0.add_edge(
                    edge.breakpoints[-1].id,
                    edge.end.id,
                    length=edge.length - edge.breakpoints[-1].distance,
                )

            # 3) Connect consecutive intermediate breakpoints
            for i in range(edge.n_breakpoints - 1):
                current_ = edge.breakpoints[i]
                next_ = edge.breakpoints[i + 1]
                length = next_.distance - current_.distance
                g0.add_edge(current_.id, next_.id, length=length)

        return nx.convert_node_labels_to_integers(g0, label_attribute="alias")

    def find(
        self,
        node: str | list[str] | None = None,
        edge: str | list[str] | None = None,
        distance: str | float | list[str | float] | None = None,
    ) -> int | list[int]:
        """Find node or breakpoint id in the generic network.

        Parameters
        ----------
        node : str | List[str], optional
            Node id(s) in the original network, by default None
        edge : str | List[str], optional
            Edge id(s) for breakpoint lookup or edge endpoint lookup, by default None
        distance : str | float | List[str | float], optional
            Distance(s) along edge for breakpoint lookup, or "start"/"end"
            for edge endpoints, by default None

        Returns
        -------
        int | List[int]
            Node or breakpoint id(s) in the generic network

        Raises
        ------
        ValueError
            If invalid combination of parameters is provided
        KeyError
            If requested node/breakpoint is not found in the network
        """
        # Determine lookup mode
        by_node = node is not None
        by_breakpoint = edge is not None or distance is not None

        if by_node and by_breakpoint:
            raise ValueError(
                "Cannot specify both 'node' and 'edge'/'distance' parameters simultaneously"
            )

        if not by_node and not by_breakpoint:
            raise ValueError("Must specify either 'node' or both 'edge' and 'distance' parameters")

        if by_node:
            # Handle node lookup
            if not isinstance(node, list):
                node = [node]
            ids = [self._id_generator.generate(node_i) for node_i in node]

        else:
            # Handle breakpoint/edge endpoint lookup
            if edge is None or distance is None:
                raise ValueError(
                    "Both 'edge' and 'distance' parameters are required for breakpoint/endpoint lookup"
                )

            if not isinstance(edge, list):
                edge = [edge]

            if not isinstance(distance, list):
                distance = [distance]

            # We can pass one edge and multiple breakpoints/endpoints
            if len(edge) == 1:
                edge = edge * len(distance)

            if len(edge) != len(distance):
                raise ValueError(
                    "Incompatible lengths of 'edge' and 'distance' arguments. One 'edge' admits multiple distances, otherwise they must be the same length."
                )

            ids = []
            for edge_i, distance_i in zip(edge, distance):
                if distance_i in ["start", "end"]:
                    # Handle edge endpoint lookup
                    if edge_i not in self._edges:
                        raise KeyError(f"Edge '{edge_i}' not found in the network.")

                    network_edge = self._edges[edge_i]
                    if distance_i == "start":
                        ids.append(network_edge.start.id)
                    else:  # distance_i == "end"
                        ids.append(network_edge.end.id)
                else:
                    # Handle breakpoint lookup
                    ids.append(self._id_generator.generate(edge=edge_i, distance=distance_i))

        # Check if all ids exist in the network
        alias_set = set(self._alias_map.keys())
        if all([id in alias_set for id in ids]):
            if len(ids) == 1:
                return self._alias_map[ids[0]]
            else:
                return [self._alias_map[id] for id in ids]
        else:
            missing_ids = [id for id in ids if id not in alias_set]
            raise KeyError(
                f"Node/breakpoint(s) {missing_ids} not found in the network. Available nodes are {alias_set}"
            )

    def recall(self, id: int | list[int]) -> dict[str, Any] | list[dict[str, Any]]:
        """Recall the original coordinates from generic network node id(s).

        Parameters
        ----------
        id : int | List[int]
            Node id(s) in the generic network

        Returns
        -------
        Dict[str, Any] | List[Dict[str, Any]]
            Original coordinates. For single input returns dict, for multiple inputs returns list of dicts.
            Dict contains coordinates:
            - For nodes: 'node' key with node id
            - For breakpoints: 'edge' and 'distance' keys with edge id and distance

        Raises
        ------
        KeyError
            If node id is not found in the network
        ValueError
            If node id string format is invalid
        """
        # Convert to list for uniform processing
        if not isinstance(id, list):
            id = [id]

        # Create reverse lookup map
        reverse_alias_map = {v: k for k, v in self._alias_map.items()}

        results = []
        for node_id in id:
            if node_id not in reverse_alias_map:
                raise KeyError(f"Node ID {node_id} not found in the network.")

            string_id = reverse_alias_map[node_id]
            coordinates = self._id_generator.parse(string_id)
            results.append(coordinates)

        # Return single dict if single input, list otherwise
        if len(results) == 1:
            return results[0]
        else:
            return results
