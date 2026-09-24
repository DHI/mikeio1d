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
from typing import TYPE_CHECKING

from ..res1d import Res1D

if TYPE_CHECKING:
    from collections.abc import Mapping

    from ..result_network import ResultGridPoint, ResultNode, ResultQuantity, ResultReach
    from ._naming import Alias

from ._results import _Results
from ._results import _Series
from ._types import NetworkReach, ReachBreakPoint


def _units_of(res: Res1D) -> dict[str, str]:
    """Read the unit abbreviation of every quantity a file declares, from its header."""
    return {
        str(quantity.Id): str(quantity.EumQuantity.UnitAbbreviation)
        for quantity in res.result_data.Quantities
    }


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


_SeriesKey = str | tuple[str, int]
"""Where a series sits in a result file, before any break point is placed.

A ``str`` is a node id. A ``(reach_id, i)`` tuple is the ``i``-th of the reach's
:func:`_ordered_gridpoints`. A companion result is keyed the same way, which is
how its series land on the main file's locations.
"""


def _ordered_gridpoints(reach: ResultReach) -> list[ResultGridPoint]:
    """Give the gridpoints a reach's break points are made from, in order along it.

    Sorted rather than taken as they come: a multi-segment reach reports its
    gridpoints one segment at a time, in the order the file lists the segments,
    which is not promised to be the order they sit in. A link-node reach has
    only the one synthetic stand-in mikeio1d gave it.
    """
    if _has_real_gridpoints(reach):
        return sorted(reach.gridpoints, key=lambda gp: gp.chainage)
    return reach.gridpoints[:1]


def _series_by_key(res: Res1D) -> dict[_SeriesKey, dict[str, _Series]]:
    """Map every node and gridpoint of a result file to the series it carries."""
    found: dict[_SeriesKey, dict[str, _Series]] = {
        node_id: _series_at(node) for node_id, node in res.nodes.items()
    }
    for reach_id, reach in res.reaches.items():
        for i, gridpoint in enumerate(_ordered_gridpoints(reach)):
            found[(reach_id, i)] = _series_at(gridpoint)
    return found


def _build_reach_breakpoints(
    reach: ResultReach,
    *,
    length: float | None,
    series_by_key: Mapping[_SeriesKey, dict[str, _Series]],
    series: dict[Alias, dict[str, _Series]],
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

    ``series`` is filled with the series reachable at each break point, taken
    from ``series_by_key``. It is collected here because this is the only place
    that knows which gridpoint a break point was made from: an EPANET reach's
    two break points are one gridpoint seen twice, and their distances come from
    a companion ``.inp``, so neither correspondence can be recovered afterwards.
    """
    gridpoints = _ordered_gridpoints(reach)
    if _has_real_gridpoints(reach):
        distances_per_gridpoint = [[gp.chainage] for gp in gridpoints]
    else:
        distances_per_gridpoint = [[0.0, length] for _ in gridpoints]

    breakpoints: list[ReachBreakPoint] = []
    for i, (gp, distances) in enumerate(zip(gridpoints, distances_per_gridpoint)):
        carried = series_by_key[(reach.name, i)]
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
    series_by_key: Mapping[_SeriesKey, dict[str, _Series]],
    units: Mapping[str, str],
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
    series_by_key : mapping of _SeriesKey to (dict of str to _Series)
        What each node and gridpoint carries, a companion's series included.
    units : mapping of str to str
        Unit abbreviation per quantity ID, a companion's included.
    lengths : dict of str to float, optional
        Reach lengths from a companion ``.inp``, which no result file carries.
    """
    lengths = lengths or {}

    # Filled as the reaches are built, since that is the only place that knows
    # which gridpoint a break point was made from.
    series: dict[Alias, dict[str, _Series]] = {}

    def _init_node(id: str) -> str:
        series[id] = series_by_key[id]
        return id

    def _build_reach(reach: ResultReach) -> NetworkReach:
        # Some formats (.resx) report no end nodes at all, and a reach without
        # them cannot be placed in a graph.
        if reach.start_node is None or reach.end_node is None:
            raise ValueError(
                f"mikeio1d reported no start/end node for reach {reach.name!r}; "
                "this result format's topology cannot be represented as a Network."
            )
        length = _resolve_reach_length(lengths.get(reach.name), reach)
        breakpoints = _build_reach_breakpoints(
            reach, length=length, series_by_key=series_by_key, series=series
        )
        return NetworkReach(
            id=reach.name,
            start=_init_node(reach.start_node),
            end=_init_node(reach.end_node),
            length=length,
            start_distance=_reach_start_distance(reach),
            breakpoints=tuple(breakpoints),
        )

    built = [_build_reach(reach) for reach in res.reaches.values()]
    return built, _Results(series=series, units=units, period=(res.start_time, res.end_time))
