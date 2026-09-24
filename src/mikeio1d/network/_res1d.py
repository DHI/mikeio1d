"""Adapt a :class:`~mikeio1d.Res1D` result file to the network element classes.

The reading itself belongs to ``Res1D``; this module only presents its topology
as nodes, reaches and breakpoints, and records where each location's timeseries
sit so they can be read when asked for.

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
from ._companions import _units_of

if TYPE_CHECKING:
    from collections.abc import Mapping
    from collections.abc import Sequence
    from datetime import datetime

    from ..result_network import ResultGridPoint, ResultNode, ResultQuantity, ResultReach
    from ..quantities import TimeSeriesId
    from ._companions import _Companion
    from ._naming import Alias

from ._types import NetworkNode, NetworkReach, ReachBreakPoint


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
    ``.inp``, so neither correspondence can be recovered afterwards.
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
        carried = _series_at(gp)
        if i < len(extra_gridpoints):
            # Disjoint from the main file's: a clash was refused when the
            # companion was opened.
            carried = {**carried, **_series_at(extra_gridpoints[i])}
        # Under every distance this gridpoint was stretched over, so both of
        # an EPANET reach's break points name the one series it really has.
        # Including a distance of None: nothing can ask for that break point by
        # name, but it is a graph node, and to_dataframe() reads every one.
        for distance in distances:
            series[(gp.reach_name, distance)] = carried
        breakpoints.extend(ReachBreakPoint(gp.reach_name, d) for d in distances)
    return breakpoints


def _load_res1d_network(
    res: Res1D,
    *,
    extra: _Companion | None = None,
    lengths: dict[str, float] | None = None,
) -> tuple[list[NetworkReach], _Results]:
    """Read a result file as reaches, and as the results a network reads through.

    Both come out of the one walk over ``res.reaches``, and neither touches a
    timeseries: a location knows what it carries from the file header alone.
    Returned together so that the series map, whose keys are
    gridpoint-to-break-point correspondences only this walk knows, is never
    assembled by a caller.

    Parameters
    ----------
    res : Res1D
        The main result file.
    extra : _Companion or None, optional
        The ``.resx`` read alongside, if there was one. Its quantities become
        readable like any other, and its header is needed for their units.
    lengths : dict of str to float, optional
        Reach lengths from a companion ``.inp``, which no result file carries.
    """
    lengths = lengths or {}

    # Filled as the reaches are built, since that is the only place that knows
    # which gridpoint a break point was made from.
    series: dict[Alias, dict[str, _Series]] = {}

    def _init_node(id: str) -> NetworkNode:
        # A node shared by several reaches is visited once per reach endpoint.
        if id not in series:
            carried = _series_at(res.nodes[id])
            if extra is not None and id in extra.nodes:
                carried = {**carried, **_series_at(extra.nodes[id])}
            series[id] = carried
        return NetworkNode(id)

    def _build_reach(reach: ResultReach) -> NetworkReach:
        # Some formats (.resx) report no end nodes at all, and a reach without
        # them cannot be placed in a graph.
        if reach.start_node is None or reach.end_node is None:
            raise ValueError(
                f"mikeio1d reported no start/end node for reach {reach.name!r}; "
                "this result format's topology cannot be represented as a Network."
            )
        length = _resolve_reach_length(lengths.get(reach.name), reach)
        breakpoints = _build_reach_breakpoints(reach, length=length, series=series, extra=extra)
        return NetworkReach(
            id=reach.name,
            start=_init_node(reach.start_node),
            end=_init_node(reach.end_node),
            length=length,
            start_distance=_reach_start_distance(reach),
            breakpoints=tuple(breakpoints),
        )

    built = [_build_reach(reach) for reach in res.reaches.values()]

    # The main file wins where both spell the same quantity, since it is the one
    # the network was opened from.
    units = {**(extra.units if extra is not None else {}), **_units_of(res)}
    return built, _Results(series=series, units=units, period=(res.start_time, res.end_time))


@dataclass(frozen=True)
class _Results:
    """What a network reads through: where each series sits, and the file header.

    Everything here comes from the headers, so holding it costs nothing, and a
    network keeps one for as long as it can read. It is shared rather than
    copied when the network is, since the ``Res1D`` its series point into holds
    .NET objects that cannot be deep-copied.

    Attributes
    ----------
    series : mapping of alias to (mapping of str to _Series)
        Every location's series, by quantity ID. A location absent from it has
        none; one mapped to an empty dict carries nothing, which is every node
        of a MIKE 11 result.
    units : mapping of str to str
        Unit abbreviation per quantity ID, over the main file and companion.
    period : tuple of datetime
        First and last timestep of the main result file.
    """

    series: Mapping[Alias, Mapping[str, _Series]]
    units: Mapping[str, str]
    period: tuple[datetime, datetime]

    def quantities_at(self, alias: Alias) -> list[str] | None:
        """Quantity IDs readable at one location, or None if it has no series."""
        carried = self.series.get(alias)
        return None if carried is None else list(carried)

    def read(self, items: Sequence[tuple[Alias, str]]) -> pd.DataFrame:
        """Read the given pairs, one batched call per file they live in.

        Each pair is one :meth:`quantities_at` has confirmed, under the network's
        own spelling of the location. The frame has one column per pair, in
        order and keeping duplicates, and each distinct series is read once
        however often it was asked for - an EPANET reach's two break points name
        the same gridpoint, so asking for both is one read, not two.
        """
        if not items:
            # Nothing asked for, nothing opened. The file's own time index would
            # be the tidier index to carry here, but reading it loads the whole
            # of the file's dynamic data, which is the one thing asking for
            # nothing should not do.
            return pd.DataFrame(index=pd.DatetimeIndex([], name="time"))

        series = [self.series[alias][quantity] for alias, quantity in items]

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
