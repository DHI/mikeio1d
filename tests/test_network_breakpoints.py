"""Test that every reach comes out of a file with break points of its own.

A break point is keyed by its reach's id, so a reach that has any gets a chain
of graph nodes to itself and stays distinct from a parallel reach between the
same two nodes. ``Network`` refuses two reaches with no break points between one
pair of nodes, and no result file can reach that state: a MIKE reach brings its
own gridpoints, and a link-node reach (EPANET, SWMM) is handed one synthetic
stand-in that is placed at both of its ends.
"""

# ruff: noqa: E402
from functools import cache
from pathlib import Path

import pytest

pytest.importorskip("networkx")

from mikeio1d import Res1D
from mikeio1d.network import Network

_TESTDATA = Path(__file__).parent / "testdata"

_FIXTURES = [
    "network.res1d",  # MIKE urban, an h-point at each end of every reach
    "network_river.res1d",  # MIKE river, gridpoints along a branch
    "network_cali.res11",
    "epanet.res",  # link-node, one synthetic gridpoint per reach
    # The only fixture with reaches running in parallel: five node pairs carry
    # more than one, among them four pumps to the WWTP and a weir beside four
    # orifices.
    "network_sirius_h2s.res1d",
]


@cache
def _open(filename):
    """Open a fixture once for every test here, topology only.

    The shape of the graph is the whole subject, and reading every timeseries of
    the largest fixture would cost seconds.
    """
    return Network.open(str(_TESTDATA / filename), companions=[])


@pytest.mark.parametrize("filename", _FIXTURES)
def test_every_reach_keeps_a_chain_of_its_own(filename):
    """A reach of n break points spans n + 1 edges, and shares none of them.

    So the edge count is one per reach plus one per break point. Two reaches
    landing on a single edge would leave it short, which is the collision
    ``Network`` refuses when neither has break points to be told apart by.
    """
    path = str(_TESTDATA / filename)
    graph = _open(filename).graph

    breakpoints = [node for node in graph.nodes if isinstance(graph.nodes[node]["address"], tuple)]

    assert graph.number_of_edges() == len(Res1D(path).reaches) + len(breakpoints)


_MIKE_FIXTURES = [f for f in _FIXTURES if f != "epanet.res"]


@pytest.mark.parametrize("filename", _FIXTURES)
def test_every_reach_lists_its_break_points_ascending(filename):
    """Break points are documented as ascending, and the graph builder counts on it.

    It reads the outermost pair as the reach's ends and each consecutive
    difference as an edge length, so a backwards chain would give negative
    lengths and nothing would say so. A multi-segment reach lists its gridpoints
    segment by segment, in no promised order.
    """
    network = _open(filename)

    unordered = [
        reach_id
        for reach_id, reach in network.reaches.items()
        if [bp.distance for bp in reach.breakpoints]
        != sorted(bp.distance for bp in reach.breakpoints)
    ]

    assert unordered == []


@pytest.mark.parametrize("filename", _MIKE_FIXTURES)
def test_a_mike_reach_keeps_every_gridpoint(filename):
    """One break point per gridpoint, so none is dropped as a link-node stand-in.

    Read as a link-node reach, a MIKE reach would lose its end gridpoint and
    carry its start's data there instead, silently.
    """
    path = str(_TESTDATA / filename)
    network = _open(filename)

    counts = {reach_id: len(reach.gridpoints) for reach_id, reach in Res1D(path).reaches.items()}

    assert {r: reach.n_breakpoints for r, reach in network.reaches.items()} == counts
