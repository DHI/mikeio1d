"""A network of nodes and reaches, addressable by the names it came with.

Reading a result file gives locations named the way the model named them: a node
id, or a reach and a position along it. :class:`Network` is addressed by those
names throughout; the integers its graph is labelled with stay the graph's own.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Iterable
    from datetime import datetime

    from pathlib import Path

    from ..res1d import Res1D
    from ._naming import Address
    from ._results import _Results

from collections.abc import Mapping
from collections.abc import Sequence
from types import MappingProxyType

import networkx as nx
import numpy as np
import pandas as pd
import xarray as xr

from ._graph import _generate_graph
from ._loader import _load_network
from ._naming import _Naming
from ._naming import _is_breakpoint
from ._types import Location
from ._types import NetworkReach


class Network:
    """A network of nodes and reaches, addressable by the names it came with.

    A result file names a location the way the model did: a node id, or a reach
    and a position along it, and every member here takes and gives those names.
    :meth:`to_networkx` is labelled with integers instead, each node carrying its name
    as the ``address`` attribute, and :meth:`resolve` gives the integer for a
    name - see :attr:`Location.graph_node`.

    Build one with :meth:`open`, which reads no timeseries. They stay in the
    file until :meth:`read` asks for them. The constructor is internal: it
    takes what a loader produces, not a file.
    """

    def __init__(self, reaches: Sequence[NetworkReach], results: _Results):
        self._results = results
        # Before the graph, whose error for a duplicate id would not name it.
        self._reaches = self._generate_reaches_dict(reaches)
        self._graph = _generate_graph(reaches)
        self._naming = _Naming(self._graph, self._reaches)

    def __repr__(self) -> str:
        out = [
            "<Network>",
            f"Reaches: {len(self._reaches)}",
            f"Nodes: {self._graph.number_of_nodes()}",
        ]
        start, end = self.period
        out += [f"Quantities: {list(self.quantities)}", f"Time: {start} - {end}"]
        return "\n".join(out)

    @classmethod
    def open(
        cls,
        res: str | Path | Res1D,
        *,
        companions: Sequence[str | Path | Res1D] | None = None,
    ) -> Network:
        """Read a network from a result file.

        Opening reads no timeseries. :meth:`read`, :meth:`to_dataframe` and
        :meth:`to_dataset` read them when asked.

        Parameters
        ----------
        res : str, Path or Res1D
            Path to a ``.res1d``, ``.res11`` or ``.res`` result file, or an
            already-opened :class:`~mikeio1d.Res1D`. A ``Res1D`` gives the
            topology; series are read from its file on disk, so edits made to
            it in memory with ``modify()`` are not seen.
        companions : sequence of str, Path or Res1D, or None, optional
            Files read alongside the result and recognised by their extension:

            * ``.resx`` -- extra EPANET results for the same network. Its node
              quantities (tank ``Volume`` and ``Volume Percentage``) are merged
              onto the matching nodes, and its reach quantities (pump
              ``efficiency``, ``energy`` and ``energy costs``) onto the matching
              reach's breakpoints.
            * ``.inp`` -- the EPANET input file, read for its ``[PIPES]``
              lengths. No result file carries a reach length, so without this one
              no reach has one.

            ``None`` *(default)* looks for them beside the result file, matching
            its folder and stem; ``[]`` reads none; a list reads exactly those.
            Only EPANET results are looked beside.

        Returns
        -------
        Network

        Raises
        ------
        NotImplementedError
            If no network can be built from the file's extension.
        ValueError
            If a companion has an extension this reader does not know, if two
            companions of the same kind are given, or if a ``.resx`` does not
            come from the same run as the result file, or if the two carry the
            same quantity at one location.

        Examples
        --------
        >>> from mikeio1d.network import Network
        >>> network = Network.open("model.res1d")  # doctest: +SKIP

        Read only the two nodes where observations exist:

        >>> network.read([("node_a", "WaterLevel"), ("node_b", "WaterLevel")])  # doctest: +SKIP

        Name the companions rather than letting them be found:

        >>> network = Network.open(  # doctest: +SKIP
        ...     "model.res",
        ...     companions=["other.resx", "other.inp"],
        ... )

        Notes
        -----
        Where a format keeps its timeseries, and so which locations carry
        them, is described per format in the user guide's network page.
        """
        return cls(*_load_network(res, companions))

    @staticmethod
    def _generate_reaches_dict(
        reaches: Sequence[NetworkReach],
    ) -> dict[str, NetworkReach]:
        by_id: dict[str, NetworkReach] = {}
        for reach in reaches:
            if reach.id in by_id:
                raise ValueError(
                    f"Two reaches share the id {reach.id!r}. A reach is addressed by its "
                    "id, and its breakpoints are keyed by it, so keeping both would drop "
                    "one of them and interleave their edges."
                )
            by_id[reach.id] = reach
        return by_id

    def to_dataframe(self) -> pd.DataFrame:
        """Read every series in the network, labelled the way :meth:`read` labels them.

        Meant for small networks: it holds every series in memory at once, and
        each call reads the file again. To read only some locations, or one
        quantity, use :meth:`read`::

            network.read(quantity="Discharge")

        Returns
        -------
        pd.DataFrame
            Time-indexed. Columns are ``(address, quantity)`` pairs, as
            :meth:`read` gives them.
        """
        items = [
            (address, quantity)
            for address in self._naming.graph_nodes
            for quantity in self._results.quantities_at(address)
        ]
        df = self._results.read(items).rename_axis(index="time")
        df.columns = pd.Index(items, tupleize_cols=False, name="item")
        return df

    def to_dataset(self) -> xr.Dataset:
        """Dataset of the timeseries, with each location's address alongside.

        Meant for small networks: it reads every series, as :meth:`to_dataframe`
        does.

        Returns
        -------
        xr.Dataset
            One variable per quantity over ``(time, graph_node)``. All of them
            share one ``graph_node`` axis, holding every location that carries
            any quantity; a variable is NaN where its location does not carry
            it. ``graph_node`` is the graph's integer, as
            :attr:`Location.graph_node` gives it, and the ``node_id``, ``reach``
            and ``position`` coordinates carry the address, so a consumer never
            has to hold on to the network to know what a column is. A node fills in ``node_id``, a
            breakpoint ``reach`` and ``position``, and the empty half says
            which it is::

                Coordinates:
                  * time        datetime64
                  * graph_node  int64       0 1 2 3 ...
                    node_id     <U16        'J1' 'J2' '' ''
                    reach       <U16        '' '' 'r1' 'r1'
                    position    float64     nan nan 0.0 24.5

            Empty when no location carries data.
        """
        df = self.to_dataframe()
        if len(df.columns) == 0:
            return xr.Dataset()
        columns_by_quantity: dict[str, list[int]] = {}
        for i, (_, quantity) in enumerate(df.columns):
            columns_by_quantity.setdefault(quantity, []).append(i)
        graph_nodes = self._naming.graph_nodes
        ds = xr.Dataset(
            {
                quantity: xr.DataArray(
                    df.iloc[:, cols].to_numpy(),
                    coords={
                        "time": df.index,
                        "graph_node": [graph_nodes[df.columns[i][0]] for i in cols],
                    },
                    dims=["time", "graph_node"],
                    attrs={"long_name": str(quantity)},
                )
                for quantity, cols in columns_by_quantity.items()
            }
        )

        node_ids, reaches, positions = [], [], []
        for graph_node in ds.graph_node.to_numpy():
            address = self._graph.nodes[int(graph_node)]["address"]
            if _is_breakpoint(address):
                reach, position = address
                node_ids.append("")
                reaches.append(reach)
                positions.append(position)
            else:
                node_ids.append(address)
                reaches.append("")
                positions.append(np.nan)
        return ds.assign_coords(
            node_id=("graph_node", np.array(node_ids, dtype=str)),
            reach=("graph_node", np.array(reaches, dtype=str)),
            position=("graph_node", np.array(positions, dtype=float)),
        )

    def to_networkx(self) -> nx.Graph:
        """Build the network as an undirected networkx graph.

        Each call builds a new graph, which the caller is free to edit. Hold on
        to it rather than calling this again.

        A reach becomes a chain of edges: its start node, its breakpoints in
        order, its end node. The graph is undirected; which way a reach runs is
        in ``reaches[reach_id].start`` and ``.end``.

        Returns
        -------
        nx.Graph
            Nodes are graph nodes, the integers :attr:`Location.graph_node`
            gives. Nodes and edges carry at least these attributes:

            * node ``address`` -- the location's address: a model node's id,
              or a ``(reach_id, position)`` breakpoint.
            * edge ``length`` -- the distance between the edge's two ends, in
              the reach's own units. ``None`` where the reach's length is not
              known, which is only on the edge into its end node: an EPANET
              pipe read without its ``.inp`` has no length.
            * edge ``boundary`` -- ``True`` where both ends are the same place,
              a breakpoint sitting on its reach's end node. Its length is
              ``0.0``.

        Examples
        --------
        >>> graph = network.to_networkx()  # doctest: +SKIP

        From a graph node back to its address:

        >>> graph.nodes[network.resolve("101").graph_node]["address"]  # doctest: +SKIP
        '101'

        The shortest route between two nodes by length. It fails where an
        edge's length is ``None``, as for EPANET without its ``.inp``:

        >>> start = network.resolve("100").graph_node  # doctest: +SKIP
        >>> end = network.resolve("99").graph_node  # doctest: +SKIP
        >>> route = nx.shortest_path(graph, start, end, weight="length")  # doctest: +SKIP
        >>> [graph.nodes[n]["address"] for n in route]  # doctest: +SKIP
        ['100', ('100l1', 0.0), ('100l1', 23.8413574216414), ('100l1', 47.6827148432828), '99']
        """
        return self._graph.copy()

    @property
    def reaches(self) -> Mapping[str, NetworkReach]:
        """The network's reaches, by the id the model gave them.

        Read-only. A mapping rather than a dict, so a reach's record may be
        built when it is looked up rather than when the network is opened.

        Returns
        -------
        Mapping[str, NetworkReach]
            Reach id to reach.

        Examples
        --------
        >>> network.reaches["10"].length  # doctest: +SKIP
        304.8
        """
        return MappingProxyType(self._reaches)

    @property
    def period(self) -> tuple[datetime, datetime]:
        """First and last timestep of the result file.

        Read from the file header, so no timeseries is loaded.

        Returns
        -------
        tuple[datetime, datetime]
            Start and end of the result file's time axis.

        Examples
        --------
        >>> network.period  # doctest: +SKIP
        (datetime.datetime(1994, 8, 7, 16, 35), datetime.datetime(1994, 8, 7, 18, 35))
        """
        return self._results.period

    @property
    def quantities(self) -> Mapping[str, str | None]:
        """Quantities readable somewhere in this network, by their units.

        The union over every location the network has, so everything named here
        can be read at some address - see :meth:`addresses`. A result file's
        header may declare more than this: a MIKE river result carries structure
        and sensor quantities that sit on neither a node nor a gridpoint, and
        nothing in a network can address them.

        Read-only, and read from the file header.

        Returns
        -------
        Mapping[str, str | None]
            Quantity ID to unit abbreviation. The unit is ``None`` where the
            file gave none.

        Examples
        --------
        >>> network.quantities  # doctest: +SKIP
        {'WaterLevel': 'm', 'Discharge': 'm^3/s'}
        """
        results = self._results
        units = results.units
        readable = {
            quantity
            for address in self._naming.graph_nodes
            for quantity in results.quantities_at(address)
        }
        # In the header's order, so the listing does not depend on the topology.
        ordered = [q for q in units if q in readable]
        ordered += sorted(readable.difference(units))
        return MappingProxyType({q: units.get(q) for q in ordered})

    def _blame_unreadable(
        self,
        items: Sequence[tuple[Address, str]],
        results: _Results,
        position_tol: float | None,
    ) -> KeyError:
        """Say which of the requested items cannot be read, and why each cannot.

        One error for all of them: how many fail, and the first ones by name.
        Kept to one line, since a KeyError renders its message through repr
        and would show newlines raw.
        """
        faults = []
        for address, quantity in items:
            found = self._naming.canonical(address, position_tol=position_tol)
            if found is None:
                faults.append(f"{address!r} - {self._naming.describe_miss(address)}")
                continue
            carried = results.quantities_at(found)
            if quantity in carried:
                continue
            if carried:
                faults.append(f"{address!r} carries {sorted(carried)}, not {quantity!r}")
            else:
                faults.append(
                    f"{address!r} carries no quantities of its own, so {quantity!r} cannot be "
                    "read there; addresses(reach=...) lists the breakpoints that can be"
                )
        shown = "; ".join(faults[:10])
        if len(faults) > 10:
            shown += f"; ... and {len(faults) - 10} more"
        return KeyError(
            f"read() cannot read {len(faults)} of the {len(items)} items asked for: {shown}. "
            "resolve() says what one location carries, and addresses(quantity=...) says where "
            "a quantity is, both without reading anything."
        )

    def read(
        self,
        items: Sequence[tuple[Address, str]] | None = None,
        *,
        quantity: str | None = None,
        position_tol: float | None = None,
    ) -> pd.DataFrame:
        """Read the series named by ``(address, quantity)`` pairs, or one quantity everywhere.

        Pass either ``items`` or ``quantity``, not both.

        Each call opens the file once, however many items it asks for. So one
        call with many items is faster than many calls with one item each.

        Parameters
        ----------
        items : sequence of (address, quantity)
            What to read. An address is a node ID, or a reach ID and a position
            along it, as :meth:`addresses` gives and :meth:`resolve` confirms.
            An empty sequence reads nothing at all, and returns an empty frame
            rather than the whole file.
        quantity : str, optional
            A quantity to read at every location that carries it, in place of
            ``items``. The same as passing
            ``[(a, quantity) for a in addresses(quantity=quantity)]``.
        position_tol : float, optional
            How far a position may be from a breakpoint's own and still mean
            it. Defaults to 1e-3, enough to absorb a rounded float. Widen it to
            snap a measured chainage onto the model's; the nearest breakpoint
            inside the window wins. Ignored for a node ID. Only with ``items``.

        Returns
        -------
        pd.DataFrame
            Time-indexed over the file's whole period, one column per element
            of ``items``, in that order and keeping duplicates. The columns are
            the items themselves, as asked for rather than as snapped, so
            ``df[items[i]]`` selects the series asked for.

        Raises
        ------
        KeyError
            If any item names a location the network does not have, or a
            quantity that location does not carry. The message says how many
            items fail and names the first ones. For ``quantity``, if no
            location in the network carries it.
        TypeError
            If neither or both of ``items`` and ``quantity`` are given, or
            ``position_tol`` is given with ``quantity``.
        ValueError
            If ``position_tol`` is negative or not finite, or if the items span
            the result file and its ``.resx`` companion and the two turn out to
            have different time axes.

        Examples
        --------
        >>> network.read([("101", "WaterLevel")])  # doctest: +SKIP

        One quantity at every location that carries it:

        >>> network.read(quantity="Discharge")  # doctest: +SKIP

        A measured chainage, snapped onto the model's nearest breakpoint:

        >>> network.read([(("100l1", 23.8), "Discharge")], position_tol=0.1)  # doctest: +SKIP

        A reach observation, whose breakpoints have to agree before one of them
        can stand for the reach:

        >>> points = network.addresses(reach="100l1", quantity="Discharge")  # doctest: +SKIP
        >>> network.read([(point, "Discharge") for point in points])  # doctest: +SKIP
        """
        if (items is None) == (quantity is None):
            raise TypeError("read() takes either items or quantity, not both and not neither.")
        if quantity is not None:
            return self._read_quantity(quantity, position_tol)

        results = self._results
        # Every item is checked before anything is read.
        resolved: list[tuple[Address, str]] = []
        for address, item_quantity in items:
            found = self._naming.canonical(address, position_tol=position_tol)
            if found is None or item_quantity not in results.quantities_at(found):
                raise self._blame_unreadable(items, results, position_tol)
            resolved.append((found, item_quantity))

        df = results.read(resolved)
        # A flat index: an address can itself be a tuple, which a MultiIndex
        # would split.
        df.columns = pd.Index(list(items), tupleize_cols=False, name="item")
        return df

    def _read_quantity(self, quantity: str, position_tol: float | None) -> pd.DataFrame:
        if position_tol is not None:
            raise TypeError(
                "read() takes position_tol only with items: a quantity is read at the "
                "addresses the network already has, so there is no position to snap."
            )
        items = [(address, quantity) for address in self.addresses(quantity=quantity)]
        if not items:
            raise KeyError(
                f"read() found no location carrying {quantity!r}. The network carries "
                f"{list(self.quantities)}."
            )
        # The addresses come from the network, so they need no resolving.
        df = self._results.read(items)
        df.columns = pd.Index(items, tupleize_cols=False, name="item")
        return df

    def addresses(
        self, *, reach: str | None = None, quantity: str | None = None
    ) -> Sequence[Address]:
        """List the addresses this network can be read at.

        Where :meth:`resolve` goes from an address to what the network knows
        about the location, this gives the addresses themselves: the names
        :meth:`read` takes.

        Parameters
        ----------
        reach : str, optional
            Only the breakpoints along this reach, in the order they sit. The
            reach's own end nodes are not among them - they are nodes, and a
            node is named by its own ID. A structure's reach keeps the type
            prefix the file gives it: ``"Weir:119w1"``, where
            ``Res1D.structures`` says ``"119w1"``. ``None`` *(default)* lists
            everything.
        quantity : str, optional
            Only locations carrying this quantity. ``None`` *(default)* does not
            filter.

        Returns
        -------
        Sequence[str | tuple[str, float]]
            Addresses, each of which :meth:`resolve` answers for and
            :meth:`read` takes. A sequence: it has a length, can be indexed and
            can be iterated more than once. Pass it to ``list()`` for a list.

        Examples
        --------
        Every breakpoint of a reach that carries discharge, which is the batch
        a reach observation has to be scored against:

        >>> network.addresses(reach="100l1", quantity="Discharge")  # doctest: +SKIP
        [('100l1', 23.8413574216414)]
        """
        results = self._results
        if reach is None:
            addresses: Iterable[Address] = self._naming.graph_nodes
        elif reach in self._reaches:
            addresses = [point.id for point in self._reaches[reach].breakpoints]
        else:
            raise KeyError(f"addresses() found {self._naming.describe_miss((reach, 0.0))}")

        if quantity is None:
            return list(addresses)
        return [address for address in addresses if quantity in results.quantities_at(address)]

    def resolve(self, address: Address, *, position_tol: float | None = None) -> Location | None:
        """Say whether a location is in this network, what it carries, and where.

        An address that is not here gives ``None`` rather than an exception.

        Parameters
        ----------
        address : str or tuple[str, float]
            A node ID, or a reach ID and a position along it. A reach's own end
            nodes are named by their IDs, which ``reaches[reach_id].start``
            and ``.end`` give. A structure's reach ID keeps the type prefix the
            file gives it, as in ``("Weir:119w1", 0.5)``.
        position_tol : float, optional
            How far a position may be from a breakpoint's own and still mean
            it. Defaults to 1e-3, enough to absorb a rounded float. Widen it to
            snap a measured chainage onto the model's; the nearest breakpoint
            inside the window wins. Ignored for a node ID.

        Returns
        -------
        Location or None
            ``None`` if there is no such location. Otherwise its address as the
            network spells it, the quantities readable there, and its graph
            node.

        Raises
        ------
        ValueError
            If ``position_tol`` is negative or not finite.

        Examples
        --------
        >>> network.resolve("101")  # doctest: +SKIP
        Location(address='101', quantities=('WaterLevel',), graph_node=5)

        >>> network.resolve(("100l1", 23.8), position_tol=0.1)  # doctest: +SKIP
        Location(address=('100l1', 23.8413574216414), quantities=('Discharge',), graph_node=3)

        >>> network.resolve("no_such_node") is None  # doctest: +SKIP
        True
        """
        found = self._naming.canonical(address, position_tol=position_tol)
        if found is None:
            return None
        return Location(
            address=found,
            quantities=self._results.quantities_at(found),
            graph_node=self._naming.graph_nodes[found],
        )
