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

    def __call__(self, node: str | int | None = None, **kwargs) -> str: ...

    def parse(self, node_id: str) -> dict[str, Any]: ...


@dataclass
class NetworkNode:
    """Node in the simplified network."""

    id: str
    data: pd.DataFrame
    boundary: dict[str, Any]

    @property
    def quantities(self) -> list[str]:
        """Quantities that are present in the node.

        Returns
        -------
        List[str]
        """
        return list(self.data.columns)


@dataclass
class EdgeBreakPoint:
    """Edge break point."""

    id: str
    data: pd.DataFrame
    distance: float


@dataclass
class NetworkEdge:
    """Edge of a network."""

    id: str
    start: NetworkNode
    end: NetworkNode
    length: float
    breakpoints: list[EdgeBreakPoint]

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
