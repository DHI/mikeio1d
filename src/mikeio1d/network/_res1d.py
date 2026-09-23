"""Adapt a :class:`~mikeio1d.Res1D` result file to the network element classes.

The reading itself belongs to ``Res1D``; this module only presents what it read
as nodes, reaches and breakpoints, and decides which locations get their
timeseries loaded.

Where a product keeps its timeseries differs, and that is what most of the
adapting is. MIKE 11 holds them on reach gridpoints rather than on nodes, so the
nodes of a ``.res11`` network carry no data of their own. EPANET is a link-node
model and holds them on a single synthetic gridpoint per reach, tied to neither
end - see :func:`_build_reach_breakpoints` for what becomes of it.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

import pandas as pd

from ..res1d import Res1D
from ._companions import _CompanionConflict
from ._source import _Source

if TYPE_CHECKING:
    from collections.abc import Mapping
    from collections.abc import Sequence
    from datetime import datetime

    from ..result_network import ResultGridPoint, ResultNode, ResultQuantity, ResultReach
    from ..quantities import TimeSeriesId
    from ._companions import _Companion
    from ._naming import Alias

from ._types import NetworkNode, NetworkReach, ReachBreakPoint

# Topology-only nodes and gridpoints all share this frame instead of each
# allocating its own. A large network has two per reach, which profiling showed
# to be the biggest single cost of a filtered load. Never mutate it in place.
_EMPTY_DATA = pd.DataFrame()


@dataclass(frozen=True)
class _Series:
    """One timeseries, and the file it has to be read from.

    Addressed by :class:`~mikeio1d.quantities.TimeSeriesId` rather than by the
    ``ResultQuantity`` it came from. Loading a companion's dynamic data replaces
    the whole ``ResultNetwork`` it hangs off (see ``ResultReader._load_file``),
    so any quantity object captured before that point is a stale handle onto a
    discarded object graph. A ``TimeSeriesId`` is inert, and every read looks it
    up afresh.
    """

    res: Res1D
    tsid: TimeSeriesId


def _quantity_at(node: ResultNode | ResultGridPoint, quantity_id: str) -> ResultQuantity:
    """Resolve a MIKE quantity ID to the ResultQuantity holding its timeseries.

    Not the same as ``getattr(node, quantity_id)``. mikeio1d attaches the
    attribute under a name it has made safe to type, replacing every character
    that cannot appear in a Python identifier, so an ID such as
    ``Volume Percentage`` is only reachable as ``Volume_Percentage``. The
    location's own map is keyed by the ID as the file spells it, which is what
    ``node.quantities`` reports and what a caller filters on.
    """
    # One ResultQuantity per ID on a node or a gridpoint; only a whole reach or a
    # collection spans several.
    return node._creator.result_quantity_map[quantity_id][0]


def _simplify_colnames(
    node: ResultNode | ResultGridPoint, quantities: set[str] | None = None
) -> pd.DataFrame:
    # We remove suffixes and indexes so the columns contain only the quantity names

    # Some formats keep no timeseries at all on some locations - MIKE 11, for instance,
    # stores everything on reach gridpoints, leaving the nodes empty. Asking mikeio1d
    # for a dataframe there raises, so return an empty one instead.
    if not node.quantities:
        return pd.DataFrame()

    # The columns in a Res1D dataframe follow the convention "Quantity:Location:Sublocation"
    # where Location refers to the node id or the reach id followed by the chainage.
    RES1D_NAME_SEP = ":"

    available = list(node.quantities)
    wanted = available if quantities is None else [q for q in available if q in quantities]

    if not wanted:
        # A location need not carry every requested quantity; it stays topology-only.
        return _EMPTY_DATA

    if len(wanted) == len(available):
        # Reading the whole location is one interop call rather than one per quantity.
        df = node.to_dataframe()
    else:
        df = pd.concat([_quantity_at(node, q).to_dataframe() for q in wanted], axis=1)

    renamer_dict = {}
    for quantity in wanted:
        column_pairs = [
            (col, quantity) for col in df.columns if quantity in col.split(RES1D_NAME_SEP)
        ]
        if len(column_pairs) != 1:
            raise ValueError(
                f"There must be exactly one column per quantity, found {column_pairs}."
            )
        old_name, new_name = column_pairs[0]
        renamer_dict[old_name] = new_name
    return df.rename(columns=renamer_dict).copy()


def _merge_extra_quantities(
    base: pd.DataFrame, extra: pd.DataFrame, *, location_id: str
) -> pd.DataFrame:
    """Append a companion file's quantities to a node's or reach's frame.

    Parameters
    ----------
    base : pd.DataFrame
        The node's or reach's frame from the main result file.
    extra : pd.DataFrame
        The same location's frame from the companion file, sharing its time index.
    location_id : str
        Node or reach ID, used in error messages.

    Returns
    -------
    pd.DataFrame

    Raises
    ------
    _CompanionConflict
        If a quantity appears in both frames. Concatenating would give the
        location two columns of the same name, which is the state
        ``_simplify_colnames`` already refuses.
    """
    if extra.empty:
        return base

    overlapping = base.columns.intersection(extra.columns)
    if len(overlapping) > 0:
        raise _CompanionConflict(
            f"Location {location_id!r} already has {sorted(overlapping)} in the "
            "main result file, so the companion file's copy cannot be merged in."
        )

    return pd.concat([base, extra], axis=1)


class Res1DNode(NetworkNode):
    def __init__(
        self,
        id: str,
        *,
        data: pd.DataFrame | None = None,
    ):
        self._id = id
        self._data = _EMPTY_DATA if data is None else data

    @property
    def id(self) -> str:
        return self._id

    @property
    def data(self) -> pd.DataFrame:
        return self._data


class GridPoint(ReachBreakPoint):
    def __init__(self, reach_id: str, chainage: float | None, data: pd.DataFrame | None = None):
        self._id = (reach_id, chainage)
        self._data = _EMPTY_DATA if data is None else data

    @property
    def id(self) -> tuple[str, float | None]:
        return self._id

    @property
    def data(self) -> pd.DataFrame:
        return self._data


def _resolve_reach_length(length: float | None, reach: ResultReach) -> float | None:
    """Resolve a reach's effective length.

    A length read from a companion input file wins, since mikeio1d has none
    to offer for the formats that need one. Zero means undefined whichever of
    the two said it: mikeio1d returns 0 when it cannot read a reach length -
    link-node models such as EPANET report this for every reach - and an input
    file is free to carry a 0 in the same spirit. Reported as undefined rather
    than as a zero-length reach, which would make length-weighted graph
    algorithms treat the reach as free, and would put a link-node reach's two
    break points at the same distance, collapsing them onto one. The two cases
    cannot be told apart upstream.
    """
    return (length if length is not None else reach.length) or None


def _has_real_gridpoints(reach: ResultReach) -> bool:
    """Whether these are the reach's own gridpoints, or one synthetic stand-in.

    mikeio1d invents a single gridpoint for the link-node formats that define
    none of their own (EPANET, SWMM). Only the source can tell the two cases
    apart, so ask it: the stand-in went to the reach that reported nothing.
    Counting what came back cannot, since a reach is free to report as few
    gridpoints as the stand-in stands for.
    """
    return any(res1d_reach.GridPoints.Count > 0 for res1d_reach in reach.res1d_reaches)


def _reach_start_distance(reach: ResultReach) -> float:
    """Resolve where the reach's start node sits, in the frame its breakpoints use.

    A MIKE reach's breakpoints are placed at their chainage, which is a
    coordinate along the whole river branch rather than an offset along this
    reach: the branch's chainage origin is a survey datum, so a modelled reach
    commonly starts thousands of metres in, and may even start below zero.
    A link-node reach has no chainage at all - its two breakpoints are placed
    0.0 and `length` apart by hand - so its frame starts at zero.
    """
    if not _has_real_gridpoints(reach):
        return 0.0

    # EPANET reports -inf rather than a chainage. Nothing places a breakpoint
    # against it, but an origin that is not a number would poison every edge
    # length on the reach, so fall back to the frame the breakpoints are in.
    origin = reach.start_chainage
    return origin if math.isfinite(origin) else 0.0


def _series_at(location: ResultNode | ResultGridPoint) -> dict[str, _Series]:
    """Map every quantity a location carries to the series holding it.

    Reading the map costs nothing - a location knows what it carries from the
    file header alone - which is what lets a network answer where a quantity
    lives without loading any of it.
    """
    series = {}
    for quantity_id in location.quantities:
        quantity = _quantity_at(location, quantity_id)
        series[quantity_id] = _Series(quantity.res1d, quantity.timeseries_id)
    return series


def _build_reach_breakpoints(
    reach: ResultReach,
    *,
    length: float | None,
    quantities: set[str] | None,
    populate_gridpoints: bool,
    series: dict[Alias, dict[str, _Series]],
    extra: _Companion | None = None,
) -> list[ReachBreakPoint]:
    """Build a reach's break points from its mikeio1d gridpoints.

    A reach with gridpoints of its own has real, independently-measured
    start/end points, so every gridpoint becomes a break point at its own
    chainage (the first/last ones end up coincident with the reach's own
    start_node/end_node - the graph builder connects them with a zero-length
    edge).

    A reach with none is a link-node model (e.g. EPANET), and the synthetic
    gridpoint mikeio1d gave it belongs to neither end - it is duplicated into
    two break points, one at each end (distance 0.0, and distance `length` if
    known or None otherwise), so the reach's own quantities (e.g. Flow) are
    reachable the same way MIKE's are. Decided in
    https://github.com/DHI/modelskill/issues/680.

    A companion ``.resx`` result (``extra``) contributes its own reach-level
    quantities (e.g. pump energy) the same way it already does for nodes,
    matched to the main file's gridpoints by index - the only real case
    today is a single-gridpoint reach against a single-gridpoint companion.

    ``series`` is filled with the series reachable at each break point. It is
    collected here because this is the only place that knows which gridpoint a
    break point was made from: an EPANET reach's two break points
    are one gridpoint seen twice, and their distances come from a companion
    ``.inp``, so neither correspondence can be recovered afterwards. Unlike
    ``data``, it ignores ``quantities`` and ``populate_gridpoints`` - what a
    location *can* offer does not depend on what this load chose to read.
    """
    if _has_real_gridpoints(reach):
        # Sorted rather than taken as they come: a multi-segment reach reports
        # its gridpoints one segment at a time, in the order the file lists the
        # segments, which is not promised to be the order they sit in.
        # ``NetworkReach.breakpoints`` is documented as ascending, and the graph
        # builder relies on it - the first and last break point are the reach's
        # outermost, and consecutive differences are edge lengths, which a
        # backwards pair would report as negative.
        unique_gridpoints = sorted(reach.gridpoints, key=lambda gp: gp.chainage)
        distances_per_gridpoint = [[gp.chainage] for gp in unique_gridpoints]
    else:
        unique_gridpoints = reach.gridpoints[:1]
        distances_per_gridpoint = [[0.0, length] for _ in unique_gridpoints]

    extra_gridpoints: list[ResultGridPoint] = []
    if extra is not None and reach.name in extra.reaches:
        # Sorted the same way, so pairing by index pairs the two files' points
        # in the same order along the reach.
        extra_gridpoints = sorted(extra.reaches[reach.name].gridpoints, key=lambda gp: gp.chainage)

    breakpoints: list[ReachBreakPoint] = []
    for i, (gp, distances) in enumerate(zip(unique_gridpoints, distances_per_gridpoint)):
        data = _simplify_colnames(gp, quantities) if populate_gridpoints else None
        if data is not None and i < len(extra_gridpoints):
            data = _merge_extra_quantities(
                data,
                _simplify_colnames(extra_gridpoints[i], quantities),
                location_id=reach.name,
            )
        carried = _series_at(gp)
        if i < len(extra_gridpoints):
            carried.update(_series_at(extra_gridpoints[i]))
        # Under every distance this gridpoint was stretched over, so both of
        # an EPANET reach's break points name the one series it really has.
        # A distance of None is not an address - nothing can ask for it.
        for distance in distances:
            if distance is not None:
                series[(gp.reach_name, distance)] = carried
        breakpoints.extend(GridPoint(gp.reach_name, d, data) for d in distances)
    return breakpoints


class Res1DReach(NetworkReach):
    """NetworkReach adapter for a mikeio1d ResultReach."""

    def __init__(
        self,
        reach: ResultReach,
        start_node: Res1DNode,
        end_node: Res1DNode,
        *,
        length: float | None = None,
        breakpoints: list[ReachBreakPoint] | None = None,
    ):
        self._id = reach.name

        # Must be checked separately: some formats (.resx) report None for both the
        # reach and the node, which the identity checks below would let through.
        if reach.start_node is None or reach.end_node is None:
            raise ValueError(
                f"mikeio1d reported no start/end node for reach {reach.name!r}; "
                "this result format's topology cannot be represented as a Network."
            )

        if start_node.id != reach.start_node:
            raise ValueError("Incorrect starting node.")
        if end_node.id != reach.end_node:
            raise ValueError("Incorrect ending node.")

        self._start = start_node
        self._end = end_node
        self._length = _resolve_reach_length(length, reach)
        self._start_distance = _reach_start_distance(reach)
        self._breakpoints = breakpoints or []

    @property
    def id(self) -> str:
        return self._id

    @property
    def start(self) -> Res1DNode:
        return self._start

    @property
    def end(self) -> Res1DNode:
        return self._end

    @property
    def length(self) -> float | None:
        return self._length

    @property
    def start_distance(self) -> float:
        return self._start_distance

    @property
    def breakpoints(self) -> list[ReachBreakPoint]:
        return self._breakpoints


def _load_res1d_network(
    res: Res1D,
    nodes: list[str],
    reaches: list[str],
    *,
    extra: _Companion | None = None,
    lengths: dict[str, float] | None = None,
    quantities: set[str] | None = None,
) -> tuple[list[Res1DReach], dict[Alias, dict[str, _Series]]]:
    """Read a result file as reaches, and as the map of where each series sits.

    Both come out of the one walk over ``res.reaches``, and neither can be had
    from the other afterwards: the reaches are what the filters let through,
    while the map records what every location could offer. Returned together so
    that the map, whose keys are gridpoint-to-break-point correspondences only
    this walk knows, is never assembled by a caller.
    """
    nodes_set = set(nodes)
    reaches_set = set(reaches)
    lengths = lengths or {}

    # Filled as the reaches are built, since that is the only place that knows
    # which gridpoint a break point was made from. Never narrowed by the filters
    # above: what a location offers is a fact about the file, not about this load.
    series: dict[Alias, dict[str, _Series]] = {}

    # In order to work with bigger files, we might want to select a subset of nodes and avoid
    # potential memory issues. For this reason, we create this intermediate step that populates
    # only the data in the passed nodes

    # A node shared by several reaches is visited once per reach endpoint, but
    # _generate_graph keeps only the first copy of its data, so read it once.
    node_data: dict[str, pd.DataFrame] = {}

    def _init_node(reach: ResultReach, is_end: bool) -> Res1DNode:
        id = reach.end_node if is_end else reach.start_node
        # Recorded for every node the graph will hold, whatever the filters let
        # through, so a caller can still read a node this load skipped.
        if id not in series:
            carried = _series_at(res.nodes[id])
            if extra is not None and id in extra.nodes:
                carried.update(_series_at(extra.nodes[id]))
            series[id] = carried
        if id in nodes_set:
            if id not in node_data:
                df = _simplify_colnames(res.nodes[id], quantities)
                # Merged here rather than up front so selective loading still
                # decides what is held in memory.
                if extra is not None and id in extra.nodes:
                    df = _merge_extra_quantities(
                        df,
                        _simplify_colnames(extra.nodes[id], quantities),
                        location_id=id,
                    )
                node_data[id] = df
            return Res1DNode(id, data=node_data[id])
        else:
            return Res1DNode(id)

    def _build_reach(reach: ResultReach) -> Res1DReach:
        reach_length = lengths.get(reach.name)
        breakpoints = _build_reach_breakpoints(
            reach,
            length=_resolve_reach_length(reach_length, reach),
            quantities=quantities,
            populate_gridpoints=reach.name in reaches_set,
            series=series,
            extra=extra,
        )
        return Res1DReach(
            reach,
            _init_node(reach, False),
            _init_node(reach, True),
            length=reach_length,
            breakpoints=breakpoints,
        )

    built = [_build_reach(reach) for reach in res.reaches.values()]
    return built, series


class _Res1DSource(_Source):
    """A :class:`~mikeio1d.network._source._Source` backed by a result file.

    Holds everything the load needs, so that :meth:`build` can produce the
    topology rather than be handed it: the main file, the filters deciding which
    locations get their timeseries, and the companions - a ``.resx`` read
    alongside, and the ``[PIPES]`` lengths from an ``.inp``, which no result file
    carries.

    Parameters
    ----------
    res : Res1D
        The main result file.
    nodes, reaches : list of str
        Which locations get their timeseries loaded. See
        :meth:`~mikeio1d.network.Network.open`.
    extra : _Companion or None, optional
        The ``.resx`` read alongside, if there was one. Its quantities become
        readable like any other, and its header is needed for their units.
    lengths : dict of str to float, optional
        Reach lengths from a companion ``.inp``.
    quantities : set of str or None, optional
        Which quantities are read at each selected location.
    """

    def __init__(
        self,
        res: Res1D,
        nodes: list[str],
        reaches: list[str],
        *,
        extra: _Companion | None = None,
        lengths: dict[str, float] | None = None,
        quantities: set[str] | None = None,
    ) -> None:
        self._res = res
        self._nodes = nodes
        self._reaches = reaches
        self._extra = extra
        self._lengths = lengths
        self._quantities = quantities
        # Filled by build(), which is the only place that knows which gridpoint
        # each break point was made from.
        self._items: dict[Alias, dict[str, _Series]] = {}

    def build(self) -> list[Res1DReach]:
        """Read the file as reaches, recording where every series sits.

        The reaches are returned and not kept: a network deep-copies them and
        shares its source, so holding them here would leave a copy's two views
        of its reaches pointing at different objects.
        """
        built, self._items = _load_res1d_network(
            self._res,
            self._nodes,
            self._reaches,
            extra=self._extra,
            lengths=self._lengths,
            quantities=self._quantities,
        )
        return built

    @property
    def period(self) -> tuple[datetime, datetime]:
        """First and last timestep of the main result file."""
        return self._res.start_time, self._res.end_time

    @property
    def units(self) -> Mapping[str, str]:
        """Unit abbreviation per quantity ID, over the main file and companion.

        The main file wins where both spell the same quantity, since it is the
        one the network was opened from.
        """
        units: dict[str, str] = {}
        for res in (None if self._extra is None else self._extra.res, self._res):
            if res is None:
                continue
            for quantity in res.result_data.Quantities:
                units[str(quantity.Id)] = str(quantity.EumQuantity.UnitAbbreviation)
        return units

    def quantities_at(self, alias: Alias) -> list[str] | None:
        """Quantity IDs readable at one location, or None if it has no series."""
        carried = self._items.get(alias)
        return None if carried is None else list(carried)

    def read(self, items: Sequence[tuple[Alias, str]]) -> pd.DataFrame:
        """Read the given pairs, one batched call per file they live in.

        Each distinct series is read once however often it was asked for - an
        EPANET reach's two break points name the same gridpoint, so asking for
        both is one read, not two.
        """
        if not items:
            # Nothing asked for, nothing opened. The file's own time index would
            # be the tidier index to carry here, but reading it loads the whole
            # of the file's dynamic data, which is the one thing asking for
            # nothing should not do.
            return pd.DataFrame(index=pd.DatetimeIndex([], name="time"))

        series = [self._items[alias][quantity] for alias, quantity in items]

        # Grouped by file, and within a file de-duplicated, so what crosses the
        # interop boundary is each distinct series exactly once.
        by_file: dict[int, tuple[Res1D, list[TimeSeriesId]]] = {}
        for item in series:
            _, tsids = by_file.setdefault(id(item.res), (item.res, []))
            if item.tsid not in tsids:
                tsids.append(item.tsid)

        columns: dict[tuple[int, TimeSeriesId], pd.Series] = {}
        for res, tsids in by_file.values():
            frame = res.read(tsids, column_mode="timeseries")
            for tsid, (_, column) in zip(tsids, frame.items()):
                columns[(id(res), tsid)] = column

        return pd.concat(
            [columns[(id(item.res), item.tsid)] for item in series],
            axis=1,
            keys=range(len(series)),
        )
