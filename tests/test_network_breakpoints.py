"""Test that every reach comes out of a file with break points of its own.

A break point is keyed by its reach's id, so a reach that has any gets a chain
of graph nodes to itself and stays distinct from a parallel reach between the
same two nodes. ``Network`` refuses two reaches with no break points between one
pair of nodes, and no result file can reach that state: a MIKE reach brings its
own gridpoints, and a link-node reach (EPANET, SWMM) is handed one synthetic
stand-in that is placed at both of its ends.
"""

# ruff: noqa: E402
from pathlib import Path

import pytest

pytest.importorskip("networkx")

from mikeio1d import Res1D
from mikeio1d.network import Network
from mikeio1d.network._res1d import _build_reach_breakpoints

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


@pytest.mark.parametrize("filename", _FIXTURES)
def test_every_reach_keeps_a_chain_of_its_own(filename):
    """A reach of n break points spans n + 1 edges, and shares none of them.

    So the edge count is one per reach plus one per break point. Two reaches
    landing on a single edge would leave it short, which is the collision
    ``Network`` refuses when neither has break points to be told apart by.
    """
    path = str(_TESTDATA / filename)
    # Topology only: the shape of the graph is the whole subject, and reading
    # every timeseries of the largest fixture would cost seconds.
    graph = Network.open(path, companions=[], nodes=[], reaches=[], quantities=[]).graph

    breakpoints = [node for node in graph.nodes if isinstance(graph.nodes[node]["alias"], tuple)]

    assert graph.number_of_edges() == len(Res1D(path).reaches) + len(breakpoints)


class _Gridpoint:
    """A gridpoint at a known chainage, carrying no timeseries."""

    def __init__(self, reach_name, chainage):
        self.reach_name = reach_name
        self.chainage = chainage
        self.quantities = {}


class _Reach:
    """A reach that reports the gridpoints it was built with as its own."""

    def __init__(self, name, chainages):
        self.name = name
        self.gridpoints = [_Gridpoint(name, chainage) for chainage in chainages]
        self.res1d_reaches = [_Res1DReach(len(chainages))]


class _Res1DReach:
    """Stands in for the .NET reach, which is asked only for its count."""

    def __init__(self, count):
        self.GridPoints = _GridPoints(count)


class _GridPoints:
    def __init__(self, count):
        self.Count = count


def test_a_two_gridpoint_reach_keeps_both():
    """Both ends were measured, so neither may be dropped for the other.

    The one case no fixture can put to the loader, and the reason it asks the
    file for its gridpoint count rather than counting what came back: a reach
    read as a link-node one would discard its end gridpoint and duplicate the
    start's data, silently. Nothing in the test data reports as few as two - a
    MIKE reach carries an h-point at each end with at least one Q-point between
    - but the count is the file's to choose. The chainages here are a branch
    coordinate, as a river reach's are, so the two readings cannot agree by
    accident.
    """
    reach = _Reach("r0", [53100.0, 53200.0])

    breakpoints = _build_reach_breakpoints(
        reach, length=100.0, quantities=None, populate_gridpoints=False
    )

    assert [bp.distance for bp in breakpoints] == [53100.0, 53200.0]


def test_gridpoints_listed_out_of_order_come_out_ascending():
    """A reach's segments are listed by the file, in whatever order it likes.

    Break points are documented as ascending and the graph builder counts on
    it, reading the outermost pair as the reach's ends and each consecutive
    difference as an edge length. Taken as they come, a reach whose segments
    were listed downstream-first would get a backwards chain and negative
    lengths, and nothing would say so.
    """
    reach = _Reach("r0", [53200.0, 53100.0, 53300.0])

    breakpoints = _build_reach_breakpoints(
        reach, length=200.0, quantities=None, populate_gridpoints=False
    )

    assert [bp.distance for bp in breakpoints] == [53100.0, 53200.0, 53300.0]
