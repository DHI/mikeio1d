"""A network of nodes and reaches, addressable by the names it came with.

Reading a result file gives locations named the way the model named them: a node
id, or a reach and a distance along it. :class:`Network` is addressed by those
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
    from ._naming import Alias
    from ._results import _Results

from collections.abc import Mapping
from collections.abc import Sequence
from types import MappingProxyType

import networkx as nx
import pandas as pd
import xarray as xr

from ._graph import _generate_graph
from ._loader import _load_network
from ._naming import _Naming, _is_break_point
from ._types import Location
from ._types import NetworkReach


class Network:
    """A network of nodes and reaches, addressable by the names it came with.

    A result file names a location the way the model did: a node id, or a reach
    and a distance along it, and every member here takes and gives those names.
    :attr:`graph` is labelled with integers instead, each node carrying its name
    as the ``alias`` attribute, and :meth:`resolve` gives the integer for a name.

    Build one with :meth:`open`, which reads a result file's topology. The
    timeseries stay in the file until :meth:`read` asks for them. The
    constructor is internal: it takes what a loader produces, not a file.
    """

    def __init__(self, reaches: Sequence[NetworkReach], results: _Results):
        self._results = results
        # Ids first: two reaches sharing one would interleave their break points
        # into a single chain, and the graph error would describe the wreckage
        # rather than the cause.
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

        Only the header and the topology are read. No timeseries is, until
        :meth:`read`, :meth:`to_dataframe` or :meth:`to_dataset` asks for one.

        Parameters
        ----------
        res : str, Path or Res1D
            Path to a ``.res1d``, ``.res11`` or ``.res`` result file, or an
            already-opened :class:`~mikeio1d.Res1D`.
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
                    "id, and its break points are keyed by it, so keeping both would drop "
                    "one of them and interleave their edges."
                )
            by_id[reach.id] = reach
        return by_id

    def to_dataframe(self, sel: str | None = None) -> pd.DataFrame:
        """Read every series in the network, labelled the way :meth:`read` labels them.

        Each call reads the result file again; to read only some locations, use
        :meth:`read`.

        Parameters
        ----------
        sel : str, optional
            Only this quantity. ``None`` *(default)* reads every quantity.

        Returns
        -------
        pd.DataFrame
            Time-indexed. Columns are ``(address, quantity)`` pairs, as
            :meth:`read` gives them, or just the addresses when ``sel`` is
            given. A break point whose distance is unknown is labelled
            ``(reach_id, None)``: no address names it, but it carries a series
            all the same.
        """
        items = [
            (alias, quantity)
            for alias in self._naming.aliases
            for quantity in self._results.quantities_at(alias)
            if sel is None or quantity == sel
        ]
        df = self._results.read(items).rename_axis(index="time")
        if sel is None:
            df.columns = pd.Index(items, tupleize_cols=False, name="item")
        else:
            df.columns = pd.Index(
                [alias for alias, _ in items], tupleize_cols=False, name="address"
            )
            df.attrs["quantity"] = sel
        return df

    def to_dataset(self) -> xr.Dataset:
        """Dataset of the timeseries, with each node's original identity alongside.

        Reads every series, as :meth:`to_dataframe` does.

        Returns
        -------
        xr.Dataset
            One variable per quantity over ``(time, node)``. ``node`` is the
            integer index the graph uses, and the ``name``, ``reach`` and
            ``distance`` coordinates carry the names the model gave the same
            locations, so a consumer never has to hold on to the network to know
            what a column is::

                Coordinates:
                  * time      datetime64
                  * node      int64     0 1 2 3 ...
                    name      <U16      'J1' 'J2' '' ''
                    reach     <U16      '' '' 'r1' 'r1'
                    distance  float64   nan nan 0.0 24.5

            Empty when no location carries data.
        """
        df = self.to_dataframe()
        if len(df.columns) == 0:
            return xr.Dataset()
        positions: dict[str, list[int]] = {}
        for i, (_, quantity) in enumerate(df.columns):
            positions.setdefault(quantity, []).append(i)
        ds = xr.Dataset(
            {
                quantity: xr.DataArray(
                    df.iloc[:, cols].to_numpy(),
                    coords={
                        "time": df.index,
                        "node": [self._naming.aliases[df.columns[i][0]] for i in cols],
                    },
                    dims=["time", "node"],
                    attrs={"long_name": str(quantity)},
                )
                for quantity, cols in positions.items()
            }
        )
        return ds.assign_coords(self._naming.identity_coords(ds.node.values))

    @property
    def graph(self) -> nx.Graph:
        """Graph of the network, read-only.

        Its lookups are built from it once, so it cannot change under them.
        ``network.graph.copy()`` gives a graph to edit.
        """
        return nx.freeze(self._graph)

    @property
    def reaches(self) -> Mapping[str, NetworkReach]:
        """The network's reaches, by the id the model gave them.

        Read-only. A reach answers for its own length, endpoints and break
        points, which is how a caller asks about a location without holding the
        result file open.

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

        Read from the file header, so this costs nothing even on a network
        opened with no timeseries at all.

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
        can be read at some address - see :meth:`locations`. A result file's
        header may declare more than this: a MIKE river result carries structure
        and sensor quantities that sit on neither a node nor a gridpoint, and
        nothing in a network can address them.

        Read-only, and free: a location knows what it carries without any of it
        being loaded.

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
            for alias in self._naming.aliases
            for quantity in results.quantities_at(alias)
        }
        # Ordered by the file's own header, so two networks over one file list
        # their shared quantities alike whatever their topology.
        ordered = [q for q in units if q in readable]
        ordered += sorted(readable.difference(units))
        return MappingProxyType({q: units.get(q) for q in ordered})

    def _blame_unreadable(
        self, items: Sequence[tuple[Address, str]], results: _Results
    ) -> KeyError:
        """Say which of the requested items cannot be read, and why each cannot.

        Every one of them, in a single error: a caller reading fifty locations
        wants one round trip, not fifty. Kept to one line, since a KeyError
        renders its message through repr and would show the newlines raw.
        """
        faults = []
        for address, quantity in items:
            alias = self._naming.canonical(address)
            if alias is None:
                faults.append(f"{address!r} - {self._naming.describe_miss(address)}")
                continue
            carried = results.quantities_at(alias)
            if quantity in carried:
                continue
            if carried:
                faults.append(f"{address!r} carries {sorted(carried)}, not {quantity!r}")
            else:
                faults.append(
                    f"{address!r} carries no quantities of its own, so {quantity!r} cannot be "
                    "read there; locations(reach=...) lists the break points that can be"
                )
        shown = "; ".join(faults[:10])
        if len(faults) > 10:
            shown += f"; ... and {len(faults) - 10} more"
        return KeyError(
            f"read() cannot read {len(faults)} of the {len(items)} items asked for: {shown}. "
            "resolve() says what one location carries, and locations(quantity=...) says where "
            "a quantity is, both without reading anything."
        )

    def read(
        self,
        items: Sequence[tuple[Address, str]],
        *,
        start: str | datetime | None = None,
        end: str | datetime | None = None,
    ) -> pd.DataFrame:
        """Read the series named by ``(address, quantity)`` pairs.

        The only member here that touches timeseries data. Everything asked for
        crosses to the result file in one batched call per file it lives in, so
        a reach's whole set of break points is one read rather than one each.

        Parameters
        ----------
        items : sequence of (address, quantity)
            What to read. An address is a node ID, or a reach ID and a distance
            along it, as :meth:`locations` gives and :meth:`resolve` confirms.
            An empty sequence reads nothing at all, and returns an empty frame
            rather than the whole file.
        start, end : str or datetime, optional
            Trim the returned frame to this window. This selects on the result
            that came back; it does not read less. MIKE 1D loads a file's whole
            dynamic data on the first read of anything in it.

        Returns
        -------
        pd.DataFrame
            Time-indexed, one column per element of ``items``, in that order and
            keeping duplicates. The columns are the items themselves, so
            ``df[items[i]]`` selects the series asked for.

        Raises
        ------
        KeyError
            If any item names a location the network does not have, or a
            quantity that location does not carry. Every failing item is named.

        Examples
        --------
        >>> network.read([("101", "WaterLevel")])  # doctest: +SKIP

        A reach observation, whose break points have to agree before one of them
        can stand for the reach:

        >>> points = network.locations(reach="100l1", quantity="Discharge")  # doctest: +SKIP
        >>> network.read([(point, "Discharge") for point in points])  # doctest: +SKIP
        """
        results = self._results
        # Resolved to the network's own spelling before anything is read, so a bad
        # item is named rather than read around, and so the results are handed only
        # pairs it has already confirmed.
        resolved: list[tuple[Alias, str]] = []
        for address, quantity in items:
            alias = self._naming.canonical(address)
            if alias is None or quantity not in results.quantities_at(alias):
                raise self._blame_unreadable(items, results)
            resolved.append((alias, quantity))

        df = results.read(resolved)
        # A flat index, so a column label is the whole (address, quantity) pair
        # the caller handed in - an address is itself a tuple, and a MultiIndex
        # would read the two apart.
        df.columns = pd.Index(list(items), tupleize_cols=False, name="item")
        return df if start is None and end is None else df.loc[start:end]

    def locations(self, *, reach: str | None = None, quantity: str | None = None) -> list[Address]:
        """List the locations this network can be read at.

        Parameters
        ----------
        reach : str, optional
            Only the break points along this reach, in the order they sit. The
            reach's own end nodes are not among them - they are nodes, and a
            node is named by its own ID. ``None`` *(default)* lists everything.
        quantity : str, optional
            Only locations carrying this quantity. ``None`` *(default)* does not
            filter.

        Returns
        -------
        list[str | tuple[str, float]]
            Addresses, each of which :meth:`resolve` answers for. A break point
            whose distance is unknown is left out: nothing can name it.

        Examples
        --------
        Every break point of a reach that carries discharge, which is the batch
        a reach observation has to be scored against:

        >>> network.locations(reach="100l1", quantity="Discharge")  # doctest: +SKIP
        [('100l1', 23.8413574216414)]
        """
        results = self._results
        if reach is None:
            aliases: Iterable[Alias] = self._naming.aliases
        elif reach in self._reaches:
            aliases = [point.id for point in self._reaches[reach].breakpoints]
        else:
            raise KeyError(f"locations() found {self._naming.describe_miss((reach, 0.0))}")

        found: list[Address] = []
        for alias in aliases:
            if _is_break_point(alias) and alias[1] is None:
                continue
            if quantity is not None and quantity not in results.quantities_at(alias):
                continue
            found.append(alias)
        return found

    def resolve(self, address: Address, *, tol: float | None = None) -> Location | None:
        """Say whether a location is in this network, what it carries, and where.

        The one lookup by name. An address that is not here is answered with
        ``None`` rather than an exception, which is what makes it usable for
        deciding whether to read at all.

        Parameters
        ----------
        address : str or tuple[str, float]
            A node ID, or a reach ID and a distance along it. A reach's own end
            nodes are named by their IDs, which ``reaches[reach_id].start``
            and ``.end`` give.
        tol : float, optional
            How far a distance may be from a break point's own and still mean
            it. Defaults to 1e-3, enough to absorb a rounded float. Widen it to
            snap a measured chainage onto the model's; the nearest break point
            inside the window wins. Ignored for a node ID.

        Returns
        -------
        Location or None
            ``None`` if there is no such location. Otherwise its address as the
            network spells it, the quantities readable there, and its graph
            integer.

        Raises
        ------
        ValueError
            If ``tol`` is negative or not finite.

        Examples
        --------
        >>> network.resolve("101")  # doctest: +SKIP
        Location(address='101', quantities=('WaterLevel',), node=5)

        >>> network.resolve(("100l1", 23.8), tol=0.1)  # doctest: +SKIP
        Location(address=('100l1', 23.8413574216414), quantities=('Discharge',), node=3)

        >>> network.resolve("no_such_node") is None  # doctest: +SKIP
        True
        """
        # The network's own spelling rather than the argument echoed, so the
        # address that comes out is the one the rest of the surface takes.
        alias = self._naming.canonical(address, tol=tol)
        if alias is None:
            return None
        return Location(
            address=alias,
            quantities=self._results.quantities_at(alias),
            node=self._naming.aliases[alias],
        )
