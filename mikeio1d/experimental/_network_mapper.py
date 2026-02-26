"""FormatMapper class."""

from __future__ import annotations

import pandas as pd

from pathlib import Path
from typing import Any

from mikeio1d import Res1D
from mikeio1d.result_network import ResultNode, ResultReach, ResultGridPoint

# from modelskill.model.protocols.network import
from mikeio1d.experimental._network_protocol import (
    NetworkEdge,
    NetworkNode,
    EdgeBreakPoint,
    NetworkNodeIdGenerator,
    NetworkMapper,
)


def _simplify_colnames(node: ResultNode | ResultGridPoint) -> pd.DataFrame:
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
    return df.rename(columns=renamer_dict).copy()


class Res1DIdGenerator(NetworkNodeIdGenerator):
    """Bidirectional mapping between network coordinates and string IDs.

    Handles conversion from network element coordinates (node ID or edge + distance)
    to unique string identifiers and vice versa.
    """

    # TODO: Doe we need to improve this? Shouldn't it be static method?
    def generate(self, node: str | int | None = None, **kwargs) -> str:
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


idgen = Res1DIdGenerator()


class Res1dNode(NetworkNode):
    def __init__(self, node: ResultNode, boundary: dict[str, ResultGridPoint]):

        self._id = idgen.generate(node.id)
        self._data = _simplify_colnames(node)
        self._boundary = {key: _simplify_colnames(point) for key, point in boundary.items()}

    @property
    def id(self) -> str:
        return self._id

    @property
    def data(self) -> pd.DataFrame:
        return self._data

    @property
    def boundary(self) -> dict[str, pd.DataFrame]:
        return self._boundary


class GridPoint(EdgeBreakPoint):
    def __init__(self, point: ResultGridPoint):

        self._id = idgen.generate(edge=point.reach_name, distance=point.chainage)
        self._data = _simplify_colnames(point)
        self.__distance = point.chainage

    @property
    def id(self) -> str:
        return self._id

    @property
    def data(self) -> pd.DataFrame:
        return self._data

    @property
    def distance(self) -> float:
        return self.__distance


class Res1dReach(NetworkEdge):
    """Edge of a network."""

    def __init__(self, reach: ResultReach, start_node: ResultNode, end_node: ResultNode):
        self._id = reach.name

        assert start_node.id == reach.start_node, "Incorrect starting node."
        assert end_node.id == reach.end_node, "Incorrect ending node."

        start_gridpoint = reach.gridpoints[0]
        end_gridpoint = reach.gridpoints[-1]
        intermediate_gridpoints = reach.gridpoints[1:-1] if len(reach.gridpoints) > 2 else []

        self._start = Res1dNode(start_node, {reach.name: start_gridpoint})
        self._end = Res1dNode(end_node, {reach.name: end_gridpoint})
        self._length = reach.length
        self._breakpoints = [GridPoint(gridpoint) for gridpoint in intermediate_gridpoints]

    @property
    def id(self) -> str:
        return self._id

    @property
    def start(self) -> Res1dNode:
        return self._start

    @property
    def end(self) -> Res1dNode:
        return self._end

    @property
    def length(self) -> float:
        return self._length

    @property
    def breakpoints(self) -> list[GridPoint]:
        return self._breakpoints


def create_res1d_mapper(res: Any) -> NetworkMapper:

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

    network = read_res1d_network(res)
    edges_dict = {
        reach_id: Res1dReach(reach, network.nodes[reach.start_node], network.nodes[reach.end_node])
        for reach_id, reach in network.reaches.items()
    }
    return NetworkMapper(edges_dict, idgen)


if __name__ == "__main__":
    path_to_res1d = "./tests/testdata/network.res1d"
    mapper = create_res1d_mapper(path_to_res1d)
    print("Mapper was created!")
