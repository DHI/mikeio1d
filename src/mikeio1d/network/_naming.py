"""Match the names a model gave its locations to the graph's nodes.

A result file names a location the way the model did: a node id, or a reach and
a position along it. This module holds the rule for when two positions mean the
same place, which place a measured position snaps onto, the integer each name has
in the graph, and the hints an error gives for a name the network does not have.

:class:`~mikeio1d.network.Network` builds one of these from its graph and keeps
it for the lifetime of the network.
"""

from __future__ import annotations

import bisect
import math

from collections.abc import Callable
from collections.abc import Mapping
from difflib import get_close_matches

import networkx as nx

from ._types import NetworkReach

# Tolerance for comparing positions along a reach, in whatever length unit the
# network uses. Two positions within it are the same place, which is what a
# tolerant lookup asks and what the graph builder asks of an edge whose ends
# coincide.
_POSITION_TOLERANCE = 1e-3

Address = str | tuple[str, float]
"""A location under the name its model gave it.

A plain ``str`` is a node id. A ``(reach_id, position)`` tuple is a breakpoint.
Nothing is both, so the shape says which it is.

Examples
--------
>>> from mikeio1d.network import Network
>>> network = Network.open("tests/testdata/network.res1d")
>>> network.resolve("101").address
'101'
>>> network.resolve(("100l1", 23.8413574216414)).address
('100l1', 23.8413574216414)
"""


def _is_breakpoint(address: Address) -> bool:
    """Whether an address names a breakpoint rather than a node."""
    return isinstance(address, tuple)


def _window(position_tol: float | None) -> float:
    """Give the snapping window a caller's ``position_tol`` asks for.

    Raises ValueError for a value that is not a distance. A value below
    :data:`_POSITION_TOLERANCE` gives that tolerance, within which a position
    names the breakpoint itself anyway.
    """
    if position_tol is None:
        return _POSITION_TOLERANCE
    if not math.isfinite(position_tol) or position_tol < 0:
        raise ValueError(
            f"position_tol must be a finite, non-negative number, got {position_tol!r}."
        )
    return max(position_tol, _POSITION_TOLERANCE)


def _nearest(known: list[float], position: float) -> float | None:
    """Find the position in an ascending list nearest to one given; None if it is empty."""
    # Only the two positions either side of the one asked for can be nearest;
    # of two equally near, the lower wins.
    i = bisect.bisect_left(known, position)
    return min(known[max(i - 1, 0) : i + 1], key=lambda d: abs(d - position), default=None)


class _Naming:
    """The addresses in a network, and their graph nodes, built once from a graph.

    Parameters
    ----------
    graph : nx.Graph
        The integer-labelled graph, each node carrying its ``address``.
    reaches : Mapping[str, NetworkReach]
        The network's reaches, by id, for telling a missing reach from a
        missing position on one.
    quantities_at : Callable[[Address], tuple[str, ...]]
        The quantities readable at an address, so a position snaps only onto a
        breakpoint carrying the quantity asked for.
    """

    def __init__(
        self,
        graph: nx.Graph,
        reaches: Mapping[str, NetworkReach],
        quantities_at: Callable[[Address], tuple[str, ...]],
    ):
        self._graph_nodes: dict[Address, int] = {
            address: graph_node for graph_node, address in graph.nodes(data="address")
        }
        # Each reach's breakpoint positions, ascending, for bisect.
        self._positions: dict[str, list[float]] = {}
        for address in self._graph_nodes:
            if _is_breakpoint(address):
                self._positions.setdefault(address[0], []).append(address[1])
        for known in self._positions.values():
            known.sort()
        self._reaches = reaches
        self._quantities_at = quantities_at

    @property
    def graph_nodes(self) -> Mapping[Address, int]:
        """Every address in the network, mapped to its graph node."""
        return self._graph_nodes

    def canonical(
        self,
        address: Address,
        *,
        position_tol: float | None = None,
        quantity: str | None = None,
    ) -> Address | None:
        """Give the network's own spelling of an address, or None if there is no such place.

        ``position_tol`` is checked first, whatever the address. An address that
        names a location itself (see :meth:`named`) answers with that location,
        or with None if it does not carry ``quantity``: a named breakpoint is
        never snapped away from. Failing that, a breakpoint is matched on
        position within ``position_tol``, among those carrying ``quantity`` if
        one is given, so a caller can snap a measured position onto the model's
        without knowing which quantities sit where on a staggered grid. The
        window never narrows below :data:`_POSITION_TOLERANCE`.

        The nearest breakpoint inside the window wins. At the default tolerance
        that is the only one there, but a caller widening the window is snapping
        a measured position onto the model's, and means the closest.
        """
        window = _window(position_tol)
        if isinstance(address, tuple) and not math.isfinite(address[1]):
            raise ValueError(f"breakpoint position must be finite, got {address[1]!r}.")
        named = self.named(address)
        if named is not None:
            return named if self._carries(named, quantity) else None
        if not _is_breakpoint(address):
            return None
        reach_id, position = address
        nearest = _nearest(self._carrying(reach_id, quantity), position)
        if nearest is None or abs(nearest - position) > window:
            return None
        return (reach_id, nearest)

    def named(self, address: Address) -> Address | None:
        """Give the location an address names itself, in the network's spelling, or None.

        A node ID names a node. A position names the breakpoint within
        :data:`_POSITION_TOLERANCE` of it, so ``("10", 0)`` names ``("10", 0.0)``
        and a rounded float names the one the file stores.
        """
        if not _is_breakpoint(address):
            return address if address in self._graph_nodes else None
        reach_id, position = address
        nearest = _nearest(self._positions.get(reach_id, []), position)
        if nearest is None or abs(nearest - position) > _POSITION_TOLERANCE:
            return None
        return (reach_id, nearest)

    def describe_miss(
        self,
        address: Address,
        *,
        position_tol: float | None = None,
        quantity: str | None = None,
        limit: int = 5,
    ) -> str:
        """Say what the network holds nearest to an address :meth:`canonical` misses.

        Names a few likely candidates rather than every name in the network:
        with ``quantity``, the positions that carry it. Every message is about
        the address as the caller wrote it.
        """
        if not _is_breakpoint(address):
            named = self.named(address)
            if named is not None:
                return self._describe_uncarried(named, quantity, limit)
            names = [key for key in self._graph_nodes if not _is_breakpoint(key)]
            close = get_close_matches(address, names, n=limit)
            if close:
                return "did you mean " + ", ".join(repr(name) for name in close) + "?"
            return f"the network has {len(names)} nodes, none named {address!r}"

        reach_id, position = address
        known = self._positions.get(reach_id, [])
        if reach_id not in self._reaches:
            return self._describe_missing_reach(reach_id, limit)
        if not known:
            return f"reach {reach_id!r} has no breakpoints"
        named = self.named(address)
        if named is not None:
            return self._describe_uncarried(named, quantity, limit)
        # Past the last breakpoint of a reach of unknown length there is no
        # end position to match, and widening the window would only snap
        # onto a breakpoint nearer the start.
        if self._reaches[reach_id].length is None and position > known[-1]:
            return (
                f"reach {reach_id!r} has no known length, so a position past its last "
                f"breakpoint ({known[-1]:g}) cannot be matched, however wide position_tol "
                "is; an EPANET pump or valve has none"
            )
        if quantity is None:
            listed = self._list_nearest(known, position, limit)
            return (
                f"nearest positions on reach {reach_id!r}: {listed} "
                "(position_tol= widens the match)"
            )
        carrying = self._carrying(reach_id, quantity)
        if not carrying:
            return f"reach {reach_id!r} carries {quantity!r} at no breakpoint"
        listed = self._list_nearest(carrying, position, limit)
        return (
            f"no breakpoint carrying {quantity!r} within position_tol="
            f"{_window(position_tol):g}; nearest carrying it: {listed} "
            "(position_tol= widens the match)"
        )

    def _describe_uncarried(self, named: Address, quantity: str | None, limit: int) -> str:
        # A location that is here but lacks the quantity. A breakpoint named
        # exactly is not snapped away from, so say where the quantity is instead.
        carried = sorted(self._quantities_at(named))
        if not carried:
            return (
                f"carries no quantities of its own, so {quantity!r} cannot be read there; "
                "addresses(reach=...) lists the breakpoints that can be"
            )
        described = f"carries {carried}, not {quantity!r}"
        if not _is_breakpoint(named):
            return described
        reach_id, position = named
        carrying = self._carrying(reach_id, quantity)
        if not carrying:
            return described
        listed = self._list_nearest(carrying, position, limit)
        return (
            f"{described}; a position naming a breakpoint is not snapped away from it. "
            f"Nearest carrying {quantity!r}: {listed}"
        )

    def _carries(self, address: Address, quantity: str | None) -> bool:
        return quantity is None or quantity in self._quantities_at(address)

    def _carrying(self, reach_id: str, quantity: str | None) -> list[float]:
        """Give a reach's breakpoint positions carrying a quantity, ascending."""
        known = self._positions.get(reach_id, [])
        if quantity is None:
            return known
        return [d for d in known if quantity in self._quantities_at((reach_id, d))]

    @staticmethod
    def _list_nearest(known: list[float], position: float, limit: int) -> str:
        nearest = sorted(sorted(known, key=lambda d: abs(d - position))[:limit])
        return ", ".join(format(d, "g") for d in nearest)

    def _describe_missing_reach(self, reach_id: str, limit: int) -> str:
        # A structure reach keeps the type prefix its file gives it
        # ("Weir:119w1"), which a caller holding the bare structure id, as
        # Res1D.structures gives it, has not typed.
        close = [known for known in self._reaches if known.partition(":")[2] == reach_id]
        close = close or get_close_matches(reach_id, list(self._reaches), n=limit)
        if close:
            listed = ", ".join(repr(known) for known in close[:limit])
            return f"the network has no reach {reach_id!r}; did you mean {listed}?"
        return f"the network has no reach {reach_id!r}"
