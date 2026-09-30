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
from ._naming import _window
from ._types import NetworkLocation
from ._types import NetworkReach


class Network:
    """A network of nodes and reaches, addressable by the names it came with.

    A result file names a location the way the model did: a node id, or a reach
    and a position along it, and every member here takes and gives those names.
    :meth:`to_networkx` is labelled with integers instead, each node carrying its name
    as the ``address`` attribute, and :meth:`resolve` gives the integer for a
    name - see :attr:`NetworkLocation.graph_node`.

    Build one with :meth:`open`, which reads no timeseries. They stay in the
    file until :meth:`read` asks for them. The constructor is internal: it
    takes what a loader produces, not a file.

    Notes
    -----
    Which locations carry series depends on the format:

    * MIKE 1D (``.res1d``): nodes and reach gridpoints both carry them.
    * MIKE 11 (``.res11``): only gridpoints do. A node carries nothing, so an
      observation at a node is read at a gridpoint beside it, which
      ``addresses(reach=...)`` lists.
    * EPANET (``.res``): a node carries its own. A pipe's are read at its start,
      ``(pipe_id, 0.0)``, and at its end, ``(pipe_id, length)``; the two give
      the same series. A pump or valve has no length, so only its start.

    Examples
    --------
    >>> from mikeio1d.network import Network
    >>> network = Network.open("tests/testdata/network.res1d")
    >>> print(network)
    <Network>
    Reaches: 118
    Nodes: 495
    Quantities: ['WaterLevel', 'Discharge']
    Time: 1994-08-07 16:35:00 - 1994-08-07 18:35:00
    """

    def __init__(self, reaches: Sequence[NetworkReach], results: _Results):
        self._results = results
        # Before the graph, whose error for a duplicate id would not name it.
        self._reaches = self._generate_reaches_dict(reaches)
        self._graph = _generate_graph(reaches)
        self._naming = _Naming(self._graph, self._reaches, results.quantities_at)

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
            already-opened :class:`~mikeio1d.Res1D`. Series are read from the
            file on disk, so edits made to a ``Res1D`` in memory with
            ``modify()`` are not seen. A ``Res1D`` opened with ``nodes=``,
            ``reaches=`` or ``quantities=`` still gives the whole network, but
            only the series its filter lets through: a location it leaves out
            is there, carrying nothing. One opened with ``time=`` or
            ``step_every=`` is not supported yet.
        companions : sequence of str, Path or Res1D, or None, optional
            Files read alongside the result. The one kind is ``.resx``: extra
            EPANET results for the same network. Its node quantities (tank
            ``Volume`` and ``Volume Percentage``) are merged onto the matching
            nodes, and its reach quantities (pump ``efficiency``, ``energy``
            and ``energy costs``) onto the matching reach's breakpoints.

            ``None`` *(default)* looks for one beside the result file, matching
            its folder and stem; ``[]`` reads none; a list reads exactly those.
            Only EPANET results are looked beside. A companion passed as a
            ``Res1D`` follows the same rules for filters as ``res``. The
            EPANET ``.inp`` input file is not a companion: reach lengths come
            from the ``.res`` itself.

        Returns
        -------
        Network

        Raises
        ------
        NotImplementedError
            If no network can be built from the file's extension, if the file
            holds catchments and no reaches, or if the result or a companion is
            a ``Res1D`` opened with ``time=`` or ``step_every=``.
        ValueError
            If a companion has an extension this reader does not know or is an
            ``.inp``, if two ``.resx`` are given, if a ``.resx`` covers a
            different period from the result file, or if the two carry the same
            quantity at one location.

        Warns
        -----
        UserWarning
            If the file holds catchments beside its reaches, which the network
            leaves out with their quantities, or nodes that end no reach, which
            it leaves out too.

        Examples
        --------
        >>> from mikeio1d.network import Network
        >>> network = Network.open("tests/testdata/network.res1d")
        >>> network.reaches["100l1"].start
        '100'

        Name the companions rather than letting them be found, or pass ``[]`` to
        read the result file on its own:

        >>> epanet = Network.open(
        ...     "tests/testdata/epanet.res",
        ...     companions=["tests/testdata/epanet.resx"],
        ... )
        >>> "Volume" in epanet.quantities
        True
        >>> alone = Network.open("tests/testdata/epanet.res", companions=[])
        >>> "Volume" in alone.quantities
        False

        An EPANET reach's length comes from the ``.res`` itself. A pump or valve
        has none:

        >>> alone.reaches["10"].length
        3209.544
        >>> alone.reaches["9"].length is None
        True

        A filtered ``Res1D`` gives the whole network, carrying only what its
        filter lets through:

        >>> from mikeio1d import Res1D
        >>> res = Res1D("tests/testdata/network.res1d", nodes=["1"], reaches=["100l1"])
        >>> filtered = Network.open(res)
        >>> filtered.resolve("1").quantities, filtered.resolve("101").quantities
        (('WaterLevel',), ())

        Notes
        -----
        Which locations carry series depends on the format; see
        :class:`Network`.

        A ``.resx`` and its result file are compared on their periods here, but
        on their time steps only when a :meth:`read` uses both: neither header
        gives the steps, and reading them would read the timeseries.
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

        Examples
        --------
        >>> network = Network.open("tests/testdata/network.res1d")
        >>> df = network.to_dataframe()
        >>> df.shape
        (110, 495)
        >>> df.columns[:2].tolist()
        [('100', 'WaterLevel'), ('99', 'WaterLevel')]
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
            :attr:`NetworkLocation.graph_node` gives it, and the ``node_id``,
            ``reach`` and ``position`` coordinates carry the address, so a consumer never
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

        Examples
        --------
        >>> network = Network.open("tests/testdata/network.res1d")
        >>> ds = network.to_dataset()
        >>> list(ds.data_vars), dict(ds.sizes)
        (['WaterLevel', 'Discharge'], {'time': 110, 'graph_node': 495})

        A column's address, from its coordinates:

        >>> graph_node = network.resolve(("100l1", 23.8), position_tol=0.1).graph_node
        >>> column = ds.sel(graph_node=graph_node)
        >>> column.node_id.item(), column.reach.item(), column.position.item()
        ('', '100l1', 23.8413574216414)
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
            Nodes are graph nodes, the integers :attr:`NetworkLocation.graph_node`
            gives. Nodes and edges carry at least these attributes:

            * node ``address`` -- the location's address: a model node's id,
              or a ``(reach_id, position)`` breakpoint.
            * edge ``length`` -- the distance between the edge's two ends, in
              the reach's own units. ``None`` where the reach's length is not
              known, which is only on the edge into its end node: an EPANET
              pump or valve has no length. networkx treats an
              edge whose weight is ``None`` as absent, so a route weighted by
              ``length`` goes around it.
            * edge ``boundary`` -- ``True`` where both ends are the same place,
              a breakpoint sitting on its reach's end node. Its length is
              ``0.0``.

        Examples
        --------
        >>> import networkx as nx
        >>> network = Network.open("tests/testdata/network.res1d")
        >>> graph = network.to_networkx()

        From a graph node back to its address:

        >>> graph.nodes[network.resolve("101").graph_node]["address"]
        '101'

        The shortest route between two nodes by length:

        >>> start = network.resolve("100").graph_node
        >>> end = network.resolve("99").graph_node
        >>> route = nx.shortest_path(graph, start, end, weight="length")
        >>> [graph.nodes[n]["address"] for n in route]
        ['100', ('100l1', 0.0), ('100l1', 23.8413574216414), ('100l1', 47.6827148432828), '99']

        Its first edge is a boundary edge, since the reach's first breakpoint
        sits on its start node:

        >>> graph.edges[route[0], route[1]]
        {'length': 0.0, 'boundary': True}

        A route by length skips an edge whose length is ``None``, as for an
        EPANET pump, and finds none where that edge was the only way:

        >>> epanet = Network.open("tests/testdata/epanet.res")
        >>> pump = epanet.reaches["9"]
        >>> start, end = epanet.resolve(pump.start).graph_node, epanet.resolve(pump.end).graph_node
        >>> nx.shortest_path(epanet.to_networkx(), start, end, weight="length")
        Traceback (most recent call last):
        ...
        networkx.exception.NetworkXNoPath: No path between 34 and 0.
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
        >>> network = Network.open("tests/testdata/network.res1d")
        >>> reach = network.reaches["100l1"]
        >>> reach.start, reach.end, reach.length
        ('100', '99', 47.6827148432828)
        """
        return MappingProxyType(self._reaches)

    @property
    def period(self) -> tuple[datetime, datetime]:
        """First and last timestep of the series this network reads.

        Every frame :meth:`read` returns spans it. Read from the file header, so
        no timeseries is loaded.

        Returns
        -------
        tuple[datetime, datetime]
            Start and end of the network's time axis.

        Examples
        --------
        >>> network = Network.open("tests/testdata/network.res1d")
        >>> network.period
        (datetime.datetime(1994, 8, 7, 16, 35), datetime.datetime(1994, 8, 7, 18, 35))
        """
        return self._results.period

    @property
    def quantities(self) -> Mapping[str, str | None]:
        """Quantities readable somewhere in this network, by their units.

        The union over every location the network has, so everything named here
        can be read at some address - see :meth:`addresses`. A result file's
        header may declare more than this: a MIKE river result carries structure
        and sensor quantities that sit on neither a node nor a gridpoint, and a
        result may carry catchment quantities. Nothing in a network can address
        them.

        Read-only, and read from the file header.

        Returns
        -------
        Mapping[str, str | None]
            Quantity ID to unit abbreviation. The unit is ``None`` where the
            file gave none.

        Examples
        --------
        >>> network = Network.open("tests/testdata/network.res1d")
        >>> dict(network.quantities)
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
        position_tol: float | None,
    ) -> KeyError:
        """Say which of the requested items cannot be read, and why each cannot.

        One error for all of them: how many fail, and the first ones by name.
        Kept to one line, since a KeyError renders its message through repr
        and would show newlines raw.
        """
        faults = []
        for address, quantity in items:
            found = self._naming.canonical(address, position_tol=position_tol, quantity=quantity)
            if found is not None:
                continue
            described = self._naming.describe_miss(
                address, position_tol=position_tol, quantity=quantity
            )
            # A location that is here is described by what it carries; one
            # that is not, by what is near it.
            joint = " " if self._naming.named(address) is not None else " - "
            faults.append(f"{address!r}{joint}{described}")
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
            it. Defaults to 1e-3, enough to absorb a rounded float, and never
            narrows below it: a position that close to a breakpoint names it,
            and is read there or refused. Widen it to snap a measured chainage
            onto the model's; the nearest breakpoint inside the window carrying
            the item's quantity wins. Checked for a node ID too, but not used.
            Only with ``items``.

        Returns
        -------
        pd.DataFrame
            Time-indexed over :attr:`period`, one column per element
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

        Notes
        -----
        A node of a MIKE 11 result carries nothing; see :class:`Network` for
        which locations carry series in each format.

        Examples
        --------
        >>> network = Network.open("tests/testdata/network.res1d")
        >>> df = network.read([("101", "WaterLevel")])
        >>> df.shape
        (110, 1)
        >>> df.columns.tolist()
        [('101', 'WaterLevel')]

        One quantity at every location that carries it:

        >>> network.read(quantity="Discharge").shape
        (110, 129)

        A measured chainage, snapped onto the model's nearest breakpoint. The
        column keeps the address asked for:

        >>> df = network.read([(("100l1", 23.8), "Discharge")], position_tol=0.1)
        >>> df.columns.tolist()
        [(('100l1', 23.8), 'Discharge')]

        A reach observation, whose breakpoints have to agree before one of them
        can stand for the reach:

        >>> points = network.addresses(reach="100l1", quantity="Discharge")
        >>> network.read([(point, "Discharge") for point in points]).columns.tolist()
        [(('100l1', 23.8413574216414), 'Discharge')]
        """
        if (items is None) == (quantity is None):
            raise TypeError("read() takes either items or quantity, not both and not neither.")
        if quantity is not None:
            return self._read_quantity(quantity, position_tol)

        _window(position_tol)
        # Every item is checked before anything is read.
        resolved: list[tuple[Address, str]] = []
        for address, item_quantity in items:
            found = self._naming.canonical(
                address, position_tol=position_tol, quantity=item_quantity
            )
            if found is None:
                raise self._blame_unreadable(items, position_tol)
            resolved.append((found, item_quantity))

        df = self._results.read(resolved)
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

        Raises
        ------
        KeyError
            If ``reach`` is not a reach of this network. The message suggests
            the reach meant, such as the prefixed id of a structure's reach.

        Examples
        --------
        >>> network = Network.open("tests/testdata/network.res1d")
        >>> network.addresses(reach="100l1")
        [('100l1', 0.0), ('100l1', 23.8413574216414), ('100l1', 47.6827148432828)]

        Every breakpoint of a reach that carries discharge, which is the batch
        a reach observation has to be scored against:

        >>> network.addresses(reach="100l1", quantity="Discharge")
        [('100l1', 23.8413574216414)]
        """
        results = self._results
        if reach is None:
            addresses: Iterable[Address] = self._naming.graph_nodes
        elif reach in self._reaches:
            addresses = self._reaches[reach].breakpoints
        else:
            raise KeyError(f"addresses() found {self._naming.describe_miss((reach, 0.0))}")

        if quantity is None:
            return list(addresses)
        return [address for address in addresses if quantity in results.quantities_at(address)]

    def resolve(
        self,
        address: Address,
        *,
        position_tol: float | None = None,
        quantity: str | None = None,
    ) -> NetworkLocation | None:
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
            it. Defaults to 1e-3, enough to absorb a rounded float, and never
            narrows below it: a position that close to a breakpoint names it.
            Widen it to snap a measured chainage onto the model's; the nearest
            breakpoint inside the window wins. Checked for a node ID too, but
            not used.
        quantity : str, optional
            Only a location carrying this quantity. A position snaps onto the
            nearest breakpoint that carries it, so a caller need not know
            which quantities sit where on a staggered grid. A position naming a
            breakpoint that lacks it, or a node lacking it, gives ``None``
            rather than a neighbour. ``None`` *(default)* snaps onto any
            breakpoint.

        Returns
        -------
        NetworkLocation or None
            ``None`` if there is no such location, or none carrying
            ``quantity``: exactly when :meth:`read` would refuse the address
            with that quantity. Otherwise its address as the network spells it,
            every quantity readable there, and its graph node.

        Raises
        ------
        ValueError
            If ``position_tol`` is negative or not finite.

        Notes
        -----
        A node of a MIKE 11 result carries nothing, so it resolves with empty
        ``quantities``; see :class:`Network` for which locations carry series in
        each format.

        Examples
        --------
        >>> network = Network.open("tests/testdata/network.res1d")
        >>> network.resolve("101")
        NetworkLocation(address='101', quantities=('WaterLevel',), graph_node=5)

        A measured chainage, snapped onto the breakpoint the file stores:

        >>> network.resolve(("100l1", 23.8), position_tol=0.1)
        NetworkLocation(address=('100l1', 23.8413574216414), quantities=('Discharge',), graph_node=3)

        With a quantity, a position snaps only onto a breakpoint carrying it.
        On this staggered grid 5.0 is nearest the water level point at 0.0, but
        discharge sits at 23.84:

        >>> network.resolve(("100l1", 5.0), position_tol=30, quantity="Discharge").address
        ('100l1', 23.8413574216414)

        A position naming a breakpoint is not snapped away from it:

        >>> network.resolve(("100l1", 0.0), position_tol=30, quantity="Discharge") is None
        True

        >>> network.resolve("no_such_node") is None
        True

        A node of a MIKE 11 result is in the network, carrying nothing:

        >>> Network.open("tests/testdata/network_cali.res11").resolve("0 CALI")
        NetworkLocation(address='0 CALI', quantities=(), graph_node=0)
        """
        found = self._naming.canonical(address, position_tol=position_tol, quantity=quantity)
        if found is None:
            return None
        return NetworkLocation(
            address=found,
            quantities=self._results.quantities_at(found),
            graph_node=self._naming.graph_nodes[found],
        )
