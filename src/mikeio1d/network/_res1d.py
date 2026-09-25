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
from pathlib import Path
from typing import TYPE_CHECKING

from ..res1d import Res1D

if TYPE_CHECKING:
    from collections.abc import Mapping

    from ..result_network import ResultGridPoint, ResultNode, ResultQuantity, ResultReach
    from ._naming import Address

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

    A length read from a companion input file wins. Zero means undefined from
    either source: mikeio1d returns 0 when it cannot read a length, as for every
    EPANET reach. A zero-length reach would look free to length-weighted graph
    algorithms, and would put a link-node reach's two break points on one spot.
    """
    return (length if length is not None else reach.length) or None


def _has_real_gridpoints(reach: ResultReach) -> bool:
    """Whether these are the reach's own gridpoints, or one synthetic stand-in.

    mikeio1d invents a single gridpoint for the link-node formats that define
    none of their own (EPANET, SWMM). Counting gridpoints cannot tell the two
    apart, so this asks the underlying reaches whether they reported any.
    """
    return any(res1d_reach.GridPoints.Count > 0 for res1d_reach in reach.res1d_reaches)


def _reach_start_distance(reach: ResultReach) -> float:
    """Resolve where the reach's start node sits, in the frame its breakpoints use.

    A MIKE reach's breakpoints sit at their chainage along the whole branch, so
    the reach can start thousands of metres in, or below zero. A link-node reach
    has no chainage, and its frame starts at zero.
    """
    if not _has_real_gridpoints(reach):
        return 0.0

    # EPANET reports -inf rather than a chainage.
    origin = reach.start_chainage
    return origin if math.isfinite(origin) else 0.0


def _series_at(location: ResultNode | ResultGridPoint) -> dict[str, _Series]:
    """Map every quantity a location carries to the series holding it.

    Read from the file header; no timeseries is loaded.
    """
    series = {}
    for quantity_id in location.quantities:
        quantity = _quantity_at(location, quantity_id)
        path = Path(str(quantity.res1d.file_path))
        series[quantity_id] = _Series(path, quantity.timeseries_id)
    return series


_SeriesKey = str | tuple[str, int]
"""Where a series sits in a result file, before any break point is placed.

A ``str`` is a node id. A ``(reach_id, i)`` tuple is the ``i``-th of the reach's
:func:`_ordered_gridpoints`. A companion result is keyed the same way, which is
how its series land on the main file's locations.
"""


def _ordered_gridpoints(reach: ResultReach) -> list[ResultGridPoint]:
    """Give the gridpoints a reach's break points are made from, in order along it.

    Sorted by chainage, since a multi-segment reach lists its gridpoints segment
    by segment in no promised order. A link-node reach has only the one
    synthetic stand-in mikeio1d gave it.
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
    series: dict[Address, dict[str, _Series]],
) -> list[ReachBreakPoint]:
    """Build a reach's break points from its mikeio1d gridpoints.

    A reach with gridpoints of its own gets one break point per gridpoint, at
    its chainage.

    A link-node reach (e.g. EPANET) has one synthetic gridpoint that belongs to
    neither end. It becomes two break points, at 0.0 and at ``length``, both
    carrying its series - or only the one at 0.0 where the length is unknown.
    See https://github.com/DHI/modelskill/issues/680.

    ``series`` is filled with what each break point carries, since only here is
    it known which gridpoint a break point was made from.
    """
    gridpoints = _ordered_gridpoints(reach)
    if _has_real_gridpoints(reach):
        distances_per_gridpoint = [[gp.chainage] for gp in gridpoints]
    else:
        ends = [0.0] if length is None else [0.0, length]
        distances_per_gridpoint = [ends for _ in gridpoints]

    breakpoints: list[ReachBreakPoint] = []
    for i, (gp, distances) in enumerate(zip(gridpoints, distances_per_gridpoint)):
        carried = series_by_key[(reach.name, i)]
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

    Both come from one walk over ``res.reaches``, since the series map depends
    on which gridpoint each break point was made from. No timeseries is read.

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

    series: dict[Address, dict[str, _Series]] = {}

    def _init_node(id: str) -> str:
        series[id] = series_by_key[id]
        return id

    def _build_reach(reach: ResultReach) -> NetworkReach:
        # Some formats (.resx) report no end nodes.
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
