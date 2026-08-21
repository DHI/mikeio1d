"""Test the frame a reach places its break points in, and the edges built from it.

A break point's distance is a position, not a size. Which frame it is a position
in belongs to the reach: an urban link measures from its own start, while a MIKE
river reach reports chainages along the whole branch it belongs to. Every edge
length has to come out the same either way.
"""

# ruff: noqa: E402
from pathlib import Path

import pandas as pd
import pytest

pytest.importorskip("networkx")

from mikeio1d.network import BasicNode, BasicReach, Network, ReachBreakPoint

_TESTDATA = Path(__file__).parent / "testdata"
_RIVER = str(_TESTDATA / "network_river.res1d")
_EPANET_RES = str(_TESTDATA / "epanet.res")

# The only fixture whose reaches carry a river chainage rather than a per-link
# offset: 'river' covers km 53.1-55.1 of its branch, 'tributary' starts 50 m in,
# and 'basin_right' starts 10 m below its branch's zero.
_OFFSET_REACHES = ["river", "tributary", "basin_right"]
_RIVER_ORIGIN = 53100.0

_EVERY_FIXTURE = [
    "network.res1d",  # urban links, each measured from its own zero
    "network_river.res1d",  # river branches, chainage along the branch
    "network_cali.res11",
    "epanet.res",  # link-node, no chainage at all
]


@pytest.fixture(scope="module")
def river():
    return Network.open(_RIVER)


def _empty_node(id):
    return BasicNode(id, pd.DataFrame())


class _Point(ReachBreakPoint):
    """A break point at a known position, carrying nothing."""

    def __init__(self, reach_id, distance):
        self._id = (reach_id, distance)

    @property
    def id(self):
        return self._id

    @property
    def data(self):
        return pd.DataFrame()


def _end_edges(network, reach_id):
    """The two edges joining a reach's own nodes to its outermost break points."""
    reach = network._reaches[reach_id]
    graph_id = network._alias_map
    leading = network.graph.edges[
        network.find(reach=reach_id, distance="start"),
        graph_id[reach.breakpoints[0].id],
    ]
    trailing = network.graph.edges[
        graph_id[reach.breakpoints[-1].id],
        network.find(reach=reach_id, distance="end"),
    ]
    return leading, trailing


def _chain_lengths(network, reach_id):
    """Every edge length along one reach, start node through to end node."""
    reach = network._reaches[reach_id]
    graph_id = network._alias_map
    chain = [
        network.find(reach=reach_id, distance="start"),
        *(graph_id[breakpoint.id] for breakpoint in reach.breakpoints),
        network.find(reach=reach_id, distance="end"),
    ]
    return [network.graph.edges[a, b]["length"] for a, b in zip(chain, chain[1:])]


class TestAReachThatDoesNotStartAtZero:
    """Its chainages are coordinates along a branch, not distances along itself."""

    @pytest.mark.parametrize("reach_id", _OFFSET_REACHES)
    def test_its_outermost_gridpoints_are_boundary_edges(self, river, reach_id):
        """A MIKE reach's first and last gridpoint sit on the reach's own ends."""
        leading, trailing = _end_edges(river, reach_id)

        assert (leading["length"], leading["boundary"]) == (0.0, True)
        assert (trailing["length"], trailing["boundary"]) == (0.0, True)

    @pytest.mark.parametrize("reach_id", _OFFSET_REACHES)
    def test_its_edges_add_up_to_its_length(self, river, reach_id):
        """The origin cancels, so the chain measures the reach and not the branch."""
        expected = river._reaches[reach_id].length

        assert sum(_chain_lengths(river, reach_id)) == pytest.approx(expected)


class TestEveryFixture:
    """What holds for a river network holds for the rest."""

    @pytest.mark.parametrize("filename", _EVERY_FIXTURE)
    def test_no_edge_has_a_negative_length(self, filename):
        """A negative length is a chainage read in the wrong frame."""
        graph = Network.open(str(_TESTDATA / filename)).graph

        lengths = [attrs["length"] for _, _, attrs in graph.edges(data=True)]

        assert [length for length in lengths if length is not None and length < 0] == []


class TestTheFrameAResultReachReports:
    """Read from the reach where there is a chainage, and zero where there is none."""

    def test_a_river_reach_starts_at_its_chainage_origin(self, river):
        assert river._reaches["river"].start_distance == pytest.approx(_RIVER_ORIGIN)

    def test_a_river_reach_ends_a_length_further_on(self, river):
        reach = river._reaches["river"]

        assert reach.end_distance == pytest.approx(_RIVER_ORIGIN + reach.length)

    def test_a_break_point_below_its_branch_zero_keeps_its_sign(self, river):
        """A position can sit below its frame's origin, where a size cannot.

        'basin_right' is modelled 10 m upstream of its branch's chainage zero,
        so its first two break points are negative. Reading their distance as
        a size - the old ``abs(distance)`` - put them 10 m and 5 m from a start
        node they in fact sit on.
        """
        reach = river._reaches["basin_right"]

        below_zero = [bp.distance for bp in reach.breakpoints if bp.distance < 0]

        assert below_zero == [-10.0, -5.0]
        assert river.recall(river.find(reach="basin_right", distance=-10.0)) == {
            "reach": "basin_right",
            "distance": -10.0,
        }

    def test_a_link_node_reach_has_no_chainage_to_report(self):
        """EPANET's synthetic gridpoints are placed by hand, from zero."""
        epanet = Network.open(_EPANET_RES, companions=[])

        assert {reach.start_distance for reach in epanet._reaches.values()} == {0.0}


class TestTheDefaultFrame:
    """A reach measured from its own start needs to say nothing at all."""

    def test_it_starts_at_zero(self):
        reach = BasicReach("r0", _empty_node("A"), _empty_node("B"), length=100.0)

        assert reach.start_distance == 0.0

    def test_it_ends_at_its_length(self):
        reach = BasicReach("r0", _empty_node("A"), _empty_node("B"), length=100.0)

        assert reach.end_distance == 100.0

    def test_it_has_no_end_without_a_length(self):
        reach = BasicReach("r0", _empty_node("A"), _empty_node("B"))

        assert reach.end_distance is None

    def test_an_interior_break_point_keeps_a_real_edge_to_each_end(self):
        """Only a break point on a reach's end is a boundary; these are not."""
        reach = BasicReach(
            "r0",
            _empty_node("A"),
            _empty_node("B"),
            length=100.0,
            breakpoints=[_Point("r0", 25.0), _Point("r0", 75.0)],
        )
        network = Network([reach])

        leading, trailing = _end_edges(network, "r0")

        assert (leading["length"], leading["boundary"]) == (25.0, False)
        assert (trailing["length"], trailing["boundary"]) == (25.0, False)


class TestTwoReachesTheGraphCannotTellApart:
    """A break point is what keeps two reaches between the same nodes distinct."""

    def test_neither_having_one_is_refused(self):
        a, b = _empty_node("A"), _empty_node("B")
        reaches = [
            BasicReach("r0", a, b, length=100.0),
            BasicReach("r1", a, b, length=250.0),
        ]

        with pytest.raises(ValueError, match="'r0' and 'r1'"):
            Network(reaches)

    def test_the_pair_is_the_same_read_backwards(self):
        """The graph is undirected, so running the other way does not help."""
        a, b = _empty_node("A"), _empty_node("B")
        reaches = [
            BasicReach("r0", a, b, length=100.0),
            BasicReach("r1", b, a, length=250.0),
        ]

        with pytest.raises(ValueError, match="'r0' and 'r1'"):
            Network(reaches)

    def test_a_break_point_each_keeps_them_apart(self):
        a, b = _empty_node("A"), _empty_node("B")
        reaches = [
            BasicReach("r0", a, b, length=100.0, breakpoints=[_Point("r0", 50.0)]),
            BasicReach("r1", a, b, length=250.0, breakpoints=[_Point("r1", 125.0)]),
        ]

        assert Network(reaches).graph.number_of_edges() == 4

    def test_sharing_an_id_is_refused(self):
        """Their break points would interleave into one chain, losing a reach."""
        a, b = _empty_node("A"), _empty_node("B")
        reaches = [
            BasicReach("r0", a, b, length=100.0, breakpoints=[_Point("r0", 50.0)]),
            BasicReach("r0", a, b, length=250.0, breakpoints=[_Point("r0", 50.0)]),
        ]

        with pytest.raises(ValueError, match="share the id 'r0'"):
            Network(reaches)
