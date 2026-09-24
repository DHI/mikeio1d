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

    from ._naming import Address
    from ._naming import Alias
    from ._res1d import _Results

from collections.abc import Mapping
from collections.abc import Sequence
from copy import deepcopy
from pathlib import Path
from types import MappingProxyType
from typing import Any

import networkx as nx
import pandas as pd
import xarray as xr

from ..res1d import Res1D
from ._companions import _companion_paths, _read_companions
from ._graph import _generate_graph
from ._naming import _Naming, _is_break_point
from ._policy import _validate_extension
from ._res1d import _load_res1d_network
from ._types import NetworkReach


def _blame_the_companions(res: Res1D, found: Sequence[Any], err: Exception) -> ValueError:
    """Name the companions in an error about them, for a caller who asked for none.

    A companion found beside the result file has to be named when it turns out
    to be the problem, or the error points at files the caller did not know were
    being read.
    """
    names = ", ".join(f"'{Path(str(companion)).name}'" for companion in found)
    return ValueError(
        f"Failed to build a network from '{Path(str(res.file_path)).name}': {err}\n"
        f"Companion files read alongside it, because they share its folder: "
        f"{names}. Pass companions=[] to read the result file on its own, or "
        "name the companions you want."
    )


class Network:
    """A network of nodes and reaches, addressable by the names it came with.

    A result file names a location the way the model did: a node id, or a reach
    and a distance along it, and every member here takes and gives those names.
    :attr:`graph` is labelled with integers instead, each node carrying its name
    as the ``alias`` attribute, and :meth:`resolve` gives the integer for a name.

    Build one with :meth:`open`, which reads a result file's topology. The
    timeseries stay in the file until :meth:`read` asks for them.
    """

    def __init__(self, reaches: Sequence[NetworkReach], results: _Results):
        self._results: _Results | None = results
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
        if self._results is None:
            out.append("Result file: released")
        else:
            start, end = self.period()
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
        MIKE 11 keeps its timeseries on reach gridpoints rather than on nodes,
        so the nodes of a ``.res11`` network carry no data of their own. Use
        ``locations(reach=...)`` to find the gridpoints to read.

        An EPANET reach carries one synthetic gridpoint, which mikeio1d gives a
        breakpoint at each end so that the reach's own quantities (``Flow``,
        ``Velocity``, ...) are reachable the way a MIKE reach's end data is. As
        a result:

        * without the ``.inp``, a reach's length is unknown, so only its first
          breakpoint (``distance=0.0``) is real; the second has a graph node
          but no address, so :meth:`resolve` and :meth:`read` cannot name it.
          The corresponding edges of :attr:`graph` are ``length=None``
        * with the ``.inp``, a pipe's second breakpoint sits at its full length
          -- both breakpoints are then addressable by distance, and the edge
          between them carries the pipe's real length. Pumps and valves keep an
          unaddressable second breakpoint even so, since ``[PIPES]`` is the only
          section carrying lengths

        Node timeseries, :meth:`to_dataframe` and :meth:`to_dataset` are
        unaffected.
        """
        if isinstance(res, (str, Path)):
            path = Path(res)
            _validate_extension(path.suffix)
            res = Res1D(str(path))
        elif isinstance(res, Res1D):
            _validate_extension(Path(res.file_path).suffix)
        else:
            raise TypeError(f"Expected a str, Path or Res1D object, got {type(res).__name__!r}")

        found, discovered = _companion_paths(res, companions)

        # Every failure a companion can cause is raised while reading it, so a
        # fault in the result file itself keeps its own message: advice to drop
        # the companions cannot help with a topology the result file does not
        # have.
        try:
            extra, lengths = _read_companions(res, found)
        except ValueError as err:
            if not discovered:
                raise
            raise _blame_the_companions(res, found, err) from err

        return cls(*_load_res1d_network(res, extra=extra, lengths=lengths))

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
        """Read every series in the network, with graph node ids as column names.

        It will be multiindex unless 'sel' is passed. Each call reads the result
        file again; to read only some locations, use :meth:`read`.

        Parameters
        ----------
        sel : Optional[str], optional
            Quantity to select, by default None

        Returns
        -------
        pd.DataFrame
            Timeseries at every graph node, columns ``(node, quantity)``.

        Raises
        ------
        ValueError
            If :meth:`release` has been called on this network.
        """
        results = self._require_results("to_dataframe()")
        # Every graph node, including a break point no address can name: it
        # carries a series all the same, and the graph has a node for it.
        columns = [
            (node_id, alias, quantity)
            for alias, node_id in self._naming.aliases.items()
            for quantity in (results.quantities_at(alias) or ())
        ]
        if not columns:
            index = pd.MultiIndex.from_arrays([[], []], names=["node", "quantity"])
            return pd.DataFrame(index=pd.Index([], name="time"), columns=index)

        df = results.read([(alias, quantity) for _, alias, quantity in columns])
        df.columns = pd.MultiIndex.from_tuples(
            [(node_id, quantity) for node_id, _, quantity in columns], names=["node", "quantity"]
        )
        df = df.rename_axis(index="time")
        if sel is None:
            return df
        else:
            df.attrs["quantity"] = sel
            return df.reorder_levels(["quantity", "node"], axis=1).loc[:, sel]

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

        Raises
        ------
        ValueError
            If :meth:`release` has been called on this network.
        """
        df_raw = self.to_dataframe()
        if len(df_raw.columns) == 0:
            return xr.Dataset()
        df = df_raw.reorder_levels(["quantity", "node"], axis=1)
        quantities = df.columns.get_level_values("quantity").unique()
        ds = xr.Dataset(
            {
                q: xr.DataArray(df[q], dims=["time", "node"], attrs={"long_name": str(q)})
                for q in quantities
            }
        )
        return ds.assign_coords(self._naming.identity_coords(ds.node.values))

    @property
    def graph(self) -> nx.Graph:
        """Graph of the network."""
        return self._graph

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

    def _require_results(self, what: str) -> _Results:
        """Give the results this network reads through, or explain why there are none.

        One way to end up here: :meth:`release` has been called. A network is
        constructed with its results, so it cannot have gone without them.
        """
        if self._results is None:
            raise ValueError(
                f"{what} needs the result file this network was opened from, and "
                "release() has let go of it. The topology is still here - graph "
                "and reaches - and opening the file again restores the rest."
            )
        return self._results

    def period(self) -> tuple[datetime, datetime]:
        """First and last timestep of the result file.

        Read from the file header, so this costs nothing even on a network
        opened with no timeseries at all.

        Returns
        -------
        tuple[datetime, datetime]
            Start and end of the result file's time axis.

        Raises
        ------
        ValueError
            If :meth:`release` has been called on this network.

        Examples
        --------
        >>> network.period()  # doctest: +SKIP
        (datetime.datetime(1994, 8, 7, 16, 35), datetime.datetime(1994, 8, 7, 18, 35))
        """
        return self._require_results("period()").period

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

        Raises
        ------
        ValueError
            If :meth:`release` has been called on this network.

        Examples
        --------
        >>> network.quantities  # doctest: +SKIP
        {'WaterLevel': 'm', 'Discharge': 'm^3/s'}
        """
        results = self._require_results("quantities")
        units = results.units
        readable = {
            quantity
            for alias in self._naming.aliases
            for quantity in (results.quantities_at(alias) or ())
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
            carried = results.quantities_at(alias) or []
            if quantity in carried:
                continue
            if carried:
                faults.append(f"{address!r} carries {sorted(carried)}, not {quantity!r}")
            else:
                faults.append(
                    f"{address!r} carries no quantities of its own, so {quantity!r} cannot be "
                    "read there - MIKE 11 keeps its timeseries on reach gridpoints rather than "
                    "on nodes, so use locations(reach=...) to find them"
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
        ValueError
            If :meth:`release` has been called on this network.

        Notes
        -----
        An EPANET reach's two break points are one gridpoint seen twice, so
        asking for both gives two identical columns from a single read.

        Examples
        --------
        >>> network.read([("101", "WaterLevel")])  # doctest: +SKIP

        A reach observation, whose break points have to agree before one of them
        can stand for the reach:

        >>> points = network.locations(reach="100l1", quantity="Discharge")  # doctest: +SKIP
        >>> network.read([(point, "Discharge") for point in points])  # doctest: +SKIP
        """
        results = self._require_results("read()")
        # Resolved to the network's own spelling before anything is read, so a bad
        # item is named rather than read around, and so the results are handed only
        # pairs it has already confirmed.
        resolved: list[tuple[Alias, str]] = []
        for address, quantity in items:
            alias = self._naming.canonical(address)
            carried = None if alias is None else results.quantities_at(alias)
            if carried is None or quantity not in carried:
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

        Raises
        ------
        ValueError
            If :meth:`release` has been called on this network.

        Examples
        --------
        Every break point of a reach that carries discharge, which is the batch
        a reach observation has to be scored against:

        >>> network.locations(reach="100l1", quantity="Discharge")  # doctest: +SKIP
        [('100l1', 23.8413574216414)]
        """
        results = self._require_results("locations()")
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
            carried = results.quantities_at(alias)
            if carried is None or (quantity is not None and quantity not in carried):
                continue
            found.append(alias)
        return found

    def resolve(self, address: Address, *, tol: float | None = None) -> dict[str, Any] | None:
        """Say whether a location is in this network, what it carries, and where.

        The one lookup by name. An address that is not here is answered with
        ``None`` rather than an exception, which is what makes it usable for
        deciding whether to read at all.

        Parameters
        ----------
        address : str or tuple[str, float]
            A node ID, or a reach ID and a distance along it. A reach's own end
            nodes are named by their IDs, which ``reaches[reach_id].start.id``
            and ``.end.id`` give.
        tol : float, optional
            How far a distance may be from a break point's own and still mean
            it. Defaults to 1e-3, enough to absorb a rounded float. Widen it to
            snap a measured chainage onto the model's; the nearest break point
            inside the window wins. Ignored for a node ID.

        Returns
        -------
        dict or None
            ``None`` if there is no such location. Otherwise:

            * ``address`` -- the network's own spelling of it, which the rest of
              the surface takes
            * ``quantities`` -- the quantity IDs readable there. An empty list
              is an answer: every node of a MIKE 11 result carries nothing,
              since that format keeps its timeseries on reach gridpoints
            * ``node`` -- the integer :attr:`graph` and :meth:`to_dataset` label
              the location with. Going back, ``graph.nodes[node]["alias"]`` is
              the address

        Raises
        ------
        ValueError
            If ``tol`` is negative or not finite, or if :meth:`release` has
            been called on this network.

        Examples
        --------
        >>> network.resolve("101")  # doctest: +SKIP
        {'address': '101', 'quantities': ['WaterLevel'], 'node': 5}

        >>> network.resolve(("100l1", 23.8), tol=0.1)  # doctest: +SKIP
        {'address': ('100l1', 23.8413574216414), 'quantities': ['Discharge'], 'node': 3}

        >>> network.resolve("no_such_node") is None  # doctest: +SKIP
        True
        """
        results = self._require_results("resolve()")
        # The network's own spelling rather than the argument echoed, so the
        # address that comes out is the one the rest of the surface takes.
        alias = self._naming.canonical(address, tol=tol)
        if alias is None:
            return None
        return {
            "address": alias,
            "quantities": results.quantities_at(alias) or [],
            "node": self._naming.aliases[alias],
        }

    def copy(self) -> Network:
        """Create a deep copy of the Network.

        The graph and the reaches are copied. The result file
        the network was opened from is shared rather than copied, so both
        networks read through one open file - see :meth:`release`.

        Returns
        -------
        Network
            Deep copy of the Network object
        """
        return deepcopy(self)

    def __deepcopy__(self, memo: dict[int, Any]) -> Network:
        """Copy everything but the result file, which is shared.

        A ``Res1D`` cannot be deep-copied at all - it holds .NET objects, and
        the attempt raises ``TypeError: cannot pickle 'Filter' object``. Sharing
        it is also the behaviour worth having: a copy is made to alter the graph,
        never to open the file a second time.
        """
        clone = self.__class__.__new__(self.__class__)
        memo[id(self)] = clone
        for key, value in self.__dict__.items():
            setattr(clone, key, value if key == "_results" else deepcopy(value, memo))
        return clone

    def release(self) -> None:
        """Let go of the result file the network was opened from.

        A network keeps that file open for its own lifetime, since every series
        is read from it on request. Releasing it frees what the file holds, at
        the cost of everything that reads or asks about series: :meth:`period`,
        :attr:`quantities`, :meth:`resolve`, :meth:`locations`, :meth:`read`,
        :meth:`to_dataframe` and :meth:`to_dataset` raise from then on.

        The topology is untouched - :attr:`graph`, with each node's ``alias``,
        and :attr:`reaches` keep working. Frames already read are the caller's
        own. Calling this twice is harmless.

        Examples
        --------
        >>> network = Network.open("model.res1d")  # doctest: +SKIP
        >>> df = network.read([("101", "WaterLevel")])  # doctest: +SKIP
        >>> network.release()  # doctest: +SKIP
        """
        self._results = None
