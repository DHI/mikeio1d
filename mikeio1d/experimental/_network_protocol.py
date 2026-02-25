from dataclasses import dataclass

import pandas as pd
from typing import Any


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
