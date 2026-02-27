"""FormatMapper class."""

from __future__ import annotations

import pandas as pd

from pathlib import Path
from typing import Any

from mikeio1d import Res1D
from mikeio1d.result_network import ResultNode, ResultGridPoint, ResultReach

from mikeio1d.experimental._network_protocol import (
    NetworkEdge,
    NetworkNode,
    EdgeBreakPoint,
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


class Res1dNode(NetworkNode):
    def __init__(self, node: ResultNode, boundary: dict[str, ResultGridPoint]):

        self._id = node.id
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

        self._id = point.reach_name
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
    return NetworkMapper(edges_dict)


if __name__ == "__main__":
    path_to_res1d = "./tests/testdata/network.res1d"
    mapper = create_res1d_mapper(path_to_res1d)
    print("Mapper was created!")
