"""FormatMapper class."""

from __future__ import annotations


import pandas as pd

from pathlib import Path
from enum import Enum
from typing import Any, Callable

from mikeio1d import Res1D
from mikeio1d.result_network import ResultNode, ResultReach, ResultGridPoint
from mikeio1d.experimental._network_protocol import (
    NetworkEdge,
    NetworkNode,
    EdgeBreakPoint,
    NetworkNodeIdGenerator,
)


class NetworkBackend(Enum):
    """Backend of network."""

    RES1D = 1
    EPANET = 2
    SWMM = 3
    CUSTOM = 4


class Res1DIdGenerator(NetworkNodeIdGenerator):
    """Bidirectional mapping between network coordinates and string IDs.

    Handles conversion from network element coordinates (node ID or edge + distance)
    to unique string identifiers and vice versa.
    """

    def __call__(self, node: str | int | None = None, **kwargs) -> str:
        """Generate a unique string ID from network coordinates.

        Parameters
        ----------
        node : str | int, optional
            Node ID in the original network, by default None

        Returns
        -------
        str
            Unique string identifier

        Raises
        ------
        ValueError
            If invalid combination of parameters is provided
        """
        by_node = node is not None
        by_distance = ("edge" in kwargs) and ("distance" in kwargs)
        if by_node == by_distance:
            raise ValueError(
                "Invalid kwarg combination: 'node' was not passed and kwargs are incomplete. "
                "Only accepted methods are either 'node' or both 'edge' and 'distance'."
            )
        if by_node:
            return f"node-{node}"

        if by_distance:
            return f"break@edge-{kwargs['edge']}-{round(kwargs['distance'], 3)}"

        # This should never be reached due to the logic above, but added for mypy
        raise ValueError("Unexpected code path reached")

    def parse(self, node_id: str) -> dict[str, Any]:
        """Parse a string ID back to its original network coordinates.

        Parameters
        ----------
        node_id : str
            The string ID to parse

        Returns
        -------
        dict[str, Any]
            Dictionary containing the original coordinates:
            - For nodes: {"node": node_id}
            - For breakpoints: {"edge": edge_id, "distance": distance}

        Raises
        ------
        ValueError
            If node ID string format is invalid
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


def read_res1d_network(res: Any) -> Res1D:
    if isinstance(res, (str, Path)):
        path = Path(res)
        if path.suffix.lower() == ".res1d":
            return Res1D(res)
        else:
            raise NotImplementedError(
                f"Unsupported file extension '{path.suffix}'. Only .res1d files are supported."
            )
    elif isinstance(res, Res1D):
        return res
    else:
        raise NotImplementedError(
            f"Unsupported type '{type(res)}'. Only Res1D files are supported."
        )


def parse_res1d_network(res: Any, id_gen: Callable[..., str]) -> dict[str, NetworkEdge]:

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
            id_gen(node.id),
            simplify_colnames(node),
            boundary={reach.name: simplify_colnames(gridpoint)},
        )

    def parse_gridpoints(reach: ResultReach) -> list[EdgeBreakPoint]:
        intermediate_gridpoints = reach.gridpoints[1:-1] if len(reach.gridpoints) > 2 else []
        return [
            EdgeBreakPoint(
                id_gen(edge=gridpoint.reach_name, distance=gridpoint.chainage),
                simplify_colnames(gridpoint),
                gridpoint.chainage,
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

    network = read_res1d_network(res)
    return {reach_id: parse_reach(reach) for reach_id, reach in network.reaches.items()}
