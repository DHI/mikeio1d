"""FormatMapper class."""

from __future__ import annotations

import networkx as nx
import pandas as pd

from pathlib import Path
from enum import Enum
from typing import (
    Optional,
    List,
    Dict,
    Any,
    KeysView,
    ValuesView,
    ItemsView,
)

from mikeio1d import Res1D
from mikeio1d.result_network import ResultReach


def node_id_generator(node: Optional[str | int] = None, **kwargs) -> str:
    """Generate the id of a network node.

    Parameters
    ----------
    node : Optional[str  |  int], optional
        node id in the original network, by default None

    Returns
    -------
    str

    Raises
    ------
    ValueError
        Error raised if kwargs are not valid.
    """
    by_node = node is not None
    by_distance = ("edge" in kwargs) and ("distance" in kwargs)
    if by_node == by_distance:
        raise ValueError(
            "Invalid kwarg combination: 'node' was not passed and kwargs are incomplete. Only accepted methods are either 'node' or both 'edge' and 'distance'."
        )
    if by_node:
        return f"node-{node}"

    if by_distance:
        return f"break@edge-{kwargs['edge']}-{round(kwargs['distance'], 3)}"

    # This should never be reached due to the logic above, but added for mypy
    raise ValueError("Unexpected code path reached")


class NetworkBackend(Enum):
    """Backend of network."""

    RES1D = 1
    EPANET = 2
    CUSTOM = 3


class NetworkNode:
    """Node in the simplified network."""

    def __init__(self, id: str, *, data: pd.DataFrame, quantities: str | List[str]):
        self._id = id
        self._quantities = [quantities] if isinstance(quantities, str) else quantities
        self._data = self._build_node_data(data)

    def _build_node_data(self, df: pd.DataFrame) -> pd.DataFrame:
        renamer_dict = {}
        for quantity in self._quantities:
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


class EdgeBreakPoint(NetworkNode):
    """Edge break point."""

    def __init__(
        self, id: str, distance: float, *, data: pd.DataFrame, quantities: str | List[str]
    ):
        self._id = id
        self._quantities = [quantities] if isinstance(quantities, str) else quantities
        self._data = self._build_node_data(data)
        self._distance = distance

    @property
    def distance(self) -> float:
        """Distance to beginning of the edge."""
        return self._distance


class NetworkEdge:
    """Edge of a network."""

    def __init__(
        self,
        id: str,
        *,
        start: NetworkNode,
        end: NetworkNode,
        breaks: List[EdgeBreakPoint],
    ):
        self.id = id
        self._start = start
        self._end = end
        self.breakpoints = breaks

    @property
    def n_breakpoints(self) -> int:
        """Number of break points in the edge."""
        return len(self.breakpoints)

    @property
    def length(self) -> float:
        """Length of edge."""
        return self.breakpoints[-1].distance - self.breakpoints[0].distance

    @property
    def start(self) -> NetworkNode:
        """Starting node of the edge."""
        return self._start

    @property
    def end(self) -> NetworkNode:
        """Ending node of the edge."""
        return self._end


class EdgeCollection:
    """Collection of edges."""

    def __init__(self, network: Any):
        self._backend = self._identify_backend(network)
        self._dict = self._load_network_as_dict(network)

    def _load_network_as_dict(self, network: Any) -> Dict[str, NetworkEdge]:
        if self._backend == NetworkBackend.RES1D:
            return self._parse_res1d_network(network)
        else:
            raise NotImplementedError(
                f"Invalid backend {self._backend.name} for network of type {type(network)}"
            )

    @staticmethod
    def _parse_res1d_network(network: Res1D) -> Dict[str, NetworkEdge]:

        def parse_reach(reach: ResultReach) -> NetworkEdge:
            return NetworkEdge(
                reach.name,
                start=NetworkNode(
                    node_id_generator(reach.start_node),
                    data=network.nodes[reach.start_node].to_dataframe(),
                    quantities=network.nodes[reach.start_node].quantities,
                ),
                end=NetworkNode(
                    node_id_generator(reach.end_node),
                    data=network.nodes[reach.end_node].to_dataframe(),
                    quantities=network.nodes[reach.end_node].quantities,
                ),
                breaks=[
                    EdgeBreakPoint(
                        node_id_generator(edge=point.reach_name, distance=point.chainage),
                        point.chainage,
                        data=point.to_dataframe(),
                        quantities=point.quantities,
                    )
                    for point in reach.gridpoints
                ],
            )

        return {reach_id: parse_reach(reach) for reach_id, reach in network.reaches.items()}

    def __getitem__(self, key: str) -> NetworkEdge:
        """Get network edge."""
        return self._dict[key]

    def __contains__(self, key: str) -> bool:
        """Check if edge ID exists in the collection."""
        return key in self._dict

    def keys(self) -> KeysView[str]:
        """Return edge IDs."""
        return self._dict.keys()

    def values(self) -> ValuesView[NetworkEdge]:
        """Return NetworkEdge objects."""
        return self._dict.values()

    def items(self) -> ItemsView[str, NetworkEdge]:
        """Return (id, edge) pairs."""
        return self._dict.items()

    def get(self, key: str, default=None) -> NetworkEdge:
        """Get edge by ID with optional default value."""
        return self._dict.get(key, default)

    @staticmethod
    def _identify_backend(res: Any) -> NetworkBackend:
        if isinstance(res, Res1D):
            return NetworkBackend.RES1D
        else:
            raise NotImplementedError(
                f"Only Res1D can be parsed, and network is of type {type(res)}"
            )

    @property
    def backend(self) -> NetworkBackend:
        """Backend of network."""
        return self._backend


class GenericNetwork:
    """Generic network structure."""

    def __init__(self, graph: nx.Graph):
        self._graph = graph.copy()
        self._df = self._build_dataframe()

    def _build_dataframe(self) -> pd.DataFrame:
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

    def __init__(self, res: Any):
        self._node_alias: set = {}
        res = self._read_network(res)
        self._edges = EdgeCollection(res)

    def _read_network(self, res: Any) -> Any:
        if isinstance(res, (str, Path)):
            path = Path(res)
            if path.suffix.lower() == ".res1d":
                return Res1D(res)
            else:
                raise NotImplementedError(
                    f"Unsupported file extension '{path.suffix}'. Only .res1d files are supported."
                )
        else:
            return res

    def map_network(self) -> GenericNetwork:
        """Return generic network object.

        Returns
        -------
        GenericNetwork
        """
        g0 = self._initialize_graph()
        self._node_alias = set(g0.nodes.keys())

        return GenericNetwork(g0)

    def _initialize_graph(self) -> nx.Graph:
        g0 = nx.Graph()
        for edge in self._edges.values():
            # Including the data at the boundaries of the nodes (if any). In Res1D
            # this means the gridpoints touching the node
            start_breakpoint = edge.breakpoints[0]
            end_breakpoint = edge.breakpoints[-1]

            # TODO: Refactor to omit these assertions
            assert start_breakpoint.distance == 0, "First breakpoint starts inside edge."
            assert end_breakpoint.distance == edge.length, "Last breakpoint ends inside edge."

            if edge._start.id not in g0.nodes:
                g0.add_node(
                    edge._start.id,
                    boundary={edge.id: start_breakpoint.data},
                    data=edge._start.data,
                )
            else:
                g0.nodes[edge._start.id]["boundary"].update({edge.id: start_breakpoint.data})

            if edge._end.id not in g0.nodes:
                g0.add_node(
                    edge._end.id, boundary={edge.id: end_breakpoint.data}, data=edge._end.data
                )
            else:
                g0.nodes[edge._end.id]["boundary"].update({edge.id: end_breakpoint.data})

            # Ensure all intermediate gridpoints (breaks[1] to breaks[n_breaks-2]) have data attributes
            for i in range(1, edge.n_breakpoints - 1):
                break_point = edge.breakpoints[i]
                g0.add_node(break_point.id, data=break_point.data)

            # Add edges connecting start/end nodes to their adjacent gridpoints
            if edge.n_breakpoints >= 2:
                g0.add_edge(
                    edge._start.id, edge.breakpoints[1].id, length=edge.breakpoints[1].distance
                )
                g0.add_edge(
                    edge.breakpoints[-2].id,
                    edge._end.id,
                    length=edge.length - edge.breakpoints[-2].distance,
                )

            # Connect consecutive intermediate gridpoints
            if edge.n_breakpoints > 2:
                for i in range(1, edge.n_breakpoints - 2):
                    length = edge.breakpoints[i + 1].distance - edge.breakpoints[i].distance
                    g0.add_edge(edge.breakpoints[i].id, edge.breakpoints[i + 1].id, length=length)

        return g0.copy()

    def find(
        self,
        node: Optional[str | List[str]] = None,
        edge: Optional[str | List[str]] = None,
        at: Optional[str | float | List[str | float]] = None,
    ) -> str | List[str]:
        """Find node or breakpoint id in the generic network.

        Parameters
        ----------
        node : Optional[str | List[str]], optional
            Node id(s) in the original network, by default None
        edge : Optional[str | List[str]], optional
            Edge id(s) for breakpoint lookup or edge endpoint lookup, by default None
        at : Optional[str | float | List[str | float]], optional
            Distance(s) along edge for breakpoint lookup, or "start"/"end"
            for edge endpoints, by default None

        Returns
        -------
        str | List[str]
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
        by_breakpoint = edge is not None or at is not None

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
            ids = [node_id_generator(node_i) for node_i in node]

        else:
            # Handle breakpoint/edge endpoint lookup
            if edge is None or at is None:
                raise ValueError(
                    "Both 'edge' and 'distance' parameters are required for breakpoint/endpoint lookup"
                )

            if not isinstance(edge, list):
                edge = [edge]

            if not isinstance(at, list):
                at = [at]

            # We can pass one edge and multiple breakpoints/endpoints
            if len(edge) == 1:
                edge = edge * len(at)

            if len(edge) != len(at):
                raise ValueError(
                    "Incompatible lengths of 'edge' and 'distance' arguments. One 'edge' admits multiple distances, otherwise they must be the same length."
                )

            ids = []
            for edge_i, distance_i in zip(edge, at):
                if distance_i in ["start", "end"]:
                    # Handle edge endpoint lookup
                    if edge_i not in self._edges:
                        raise KeyError(f"Edge '{edge_i}' not found in the network.")

                    network_edge = self._edges[edge_i]
                    if distance_i == "start":
                        ids.append(network_edge._start.id)
                    else:  # distance_i == "end"
                        ids.append(network_edge._end.id)
                else:
                    # Handle breakpoint lookup
                    ids.append(node_id_generator(edge=edge_i, distance=distance_i))

        # Check if all ids exist in the network
        if all([id in self._node_alias for id in ids]):
            if len(ids) == 1:
                return ids[0]
            else:
                return ids
        else:
            missing_ids = [id for id in ids if id not in self._node_alias]
            raise KeyError(
                f"Node/breakpoint(s) {missing_ids} not found in the network. Available nodes are {self._node_alias}"
            )
