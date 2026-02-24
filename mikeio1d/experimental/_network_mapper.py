"""FormatMapper class."""

from __future__ import annotations

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
    TYPE_CHECKING,
)

from mikeio1d import Res1D
from mikeio1d.result_network import ResultNode, ResultReach, ResultGridPoint

if TYPE_CHECKING:
    import networkx as nx
    import xarray as xr


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


def parse_node_id(node_id: str) -> Dict[str, Any]:
    """Parse a node ID string back to its original coordinates.

    Parameters
    ----------
    node_id : str
        The string ID to parse

    Returns
    -------
    Dict[str, Any]
        Dictionary containing the original coordinates
    """
    if node_id.startswith("node-"):
        return {"node": node_id[5:]}
    elif node_id.startswith("break@edge-"):
        # Format: break@edge-{edge}-{distance}
        # Find the last hyphen to separate edge name from distance
        remaining = node_id[11:]  # Remove "break@edge-"
        last_hyphen = remaining.rfind("-")
        if last_hyphen == -1:
            raise ValueError(f"Invalid breakpoint ID format: {node_id}")
        edge = remaining[:last_hyphen]
        distance = float(remaining[last_hyphen + 1 :])
        return {"edge": edge, "distance": distance}
    else:
        raise ValueError(f"Unknown node ID format: {node_id}")


class NetworkBackend(Enum):
    """Backend of network."""

    RES1D = 1
    EPANET = 2
    SWMM = 3
    CUSTOM = 4


class NetworkNode:
    """Node in the simplified network."""

    def __init__(self, id: str, data: pd.DataFrame, *, boundary: Optional[Dict[str, Any]] = {}):
        self._id = id
        self._data = data
        self._boundary = boundary

    @property
    def quantities(self) -> List[str]:
        """Quantities that are present in the node.

        Returns
        -------
        List[str]
        """
        return list(self._data.columns)

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

    @property
    def boundary(self) -> Dict[str, pd.DataFrame]:
        """Boundary of node."""
        return self._boundary


class EdgeBreakPoint(NetworkNode):
    """Edge break point."""

    def __init__(self, id: str, distance: float, data: pd.DataFrame):
        super().__init__(id, data)  # Call parent constructor
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
        start: NetworkNode,
        end: NetworkNode,
        length: float,
        breaks: List[EdgeBreakPoint],
    ):
        self._id = id
        self._start = start
        self._end = end
        self._length = length
        self.breakpoints = breaks

    @property
    def n_breakpoints(self) -> int:
        """Number of break points in the edge."""
        return len(self.breakpoints)

    @property
    def length(self) -> float:
        """Length of edge."""
        return self._length

    @property
    def start(self) -> NetworkNode:
        """Starting node of the edge."""
        return self._start

    @property
    def end(self) -> NetworkNode:
        """Ending node of the edge."""
        return self._end

    @property
    def id(self) -> str:
        """Id of edge."""
        return self._id


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

        def simplify_colnames(node: ResultNode | ResultGridPoint) -> pd.DataFrame:
            # We remove suffixes and indexes so the columns contain only the quantities
            df = node.to_dataframe()
            quantities = node.quantities
            renamer_dict = {}
            for quantity in quantities:
                relevant_columns = [col for col in df.columns if quantity in col]
                if len(relevant_columns) != 1:
                    raise ValueError(
                        f"There must be exactly one column per quantity, found {relevant_columns}."
                    )
                renamer_dict[relevant_columns[0]] = quantity
            return df.rename(columns=renamer_dict, copy=True)

        def parse_end(reach: ResultReach, idx: int) -> NetworkNode:
            ends = (reach.start_node, reach.end_node)
            node: ResultNode = network.nodes[ends[idx]]
            # By definition, the first and last gridpoint in a reach are at distance
            # 0 and 'length' from the start and end node respectively, effectively overlapping with
            # the start and end nodes in a 1d representation.
            gridpoint = reach.gridpoints[idx]
            return NetworkNode(
                node_id_generator(node.id),
                simplify_colnames(node),
                boundary={reach.name: simplify_colnames(gridpoint)},
            )

        def parse_gridpoints(reach: ResultReach) -> List[EdgeBreakPoint]:
            intermediate_gridpoints = reach.gridpoints[1:-1] if len(reach.gridpoints) > 2 else []
            return [
                EdgeBreakPoint(
                    node_id_generator(edge=gridpoint.reach_name, distance=gridpoint.chainage),
                    gridpoint.chainage,
                    simplify_colnames(gridpoint),
                )
                for gridpoint in intermediate_gridpoints
            ]

        def parse_reach(reach: ResultReach) -> NetworkEdge:

            return NetworkEdge(
                reach.name,
                parse_end(reach, 0),
                parse_end(reach, -1),
                reach.length,
                parse_gridpoints(reach),
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
        df.index.name = "time"
        return df.copy()

    def to_dataframe(self, sel: Optional[str] = None) -> pd.DataFrame:
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
    def quantities(self) -> List[str]:
        """Quantities present in data.

        Returns
        -------
        List[str]
            List of quantities
        """
        return list(self.to_dataframe().columns.get_level_values(1).unique())


class NetworkMapper:
    """Mapper class to transform Res1D to a general network coord system."""

    def __init__(self, res: Any):
        self._alias_map: Dict[int, str] = {}
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
        self._alias_map = {g0.nodes[id]["alias"]: id for id in g0.nodes()}

        return GenericNetwork(g0)

    def _initialize_graph(self) -> nx.Graph:
        import networkx as nx

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
        node: Optional[str | List[str]] = None,
        edge: Optional[str | List[str]] = None,
        distance: Optional[str | float | List[str | float]] = None,
    ) -> int | List[int]:
        """Find node or breakpoint id in the generic network.

        Parameters
        ----------
        node : Optional[str | List[str]], optional
            Node id(s) in the original network, by default None
        edge : Optional[str | List[str]], optional
            Edge id(s) for breakpoint lookup or edge endpoint lookup, by default None
        distance : Optional[str | float | List[str | float]], optional
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
            ids = [node_id_generator(node_i) for node_i in node]

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
                    ids.append(node_id_generator(edge=edge_i, distance=distance_i))

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

    def recall(self, id: int | List[int]) -> Dict[str, Any] | List[Dict[str, Any]]:
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
            coordinates = parse_node_id(string_id)
            results.append(coordinates)

        # Return single dict if single input, list otherwise
        if len(results) == 1:
            return results[0]
        else:
            return results
