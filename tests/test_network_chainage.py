"""Test the frame a reach places its breakpoints in, and the edges built from it.

A breakpoint's position is a place, not a size. Which frame it is a position
in belongs to the reach: an urban link measures from its own start, while a MIKE
river reach reports chainages along the whole branch it belongs to. Every edge
length has to come out the same either way.
"""

# ruff: noqa: E402
from pathlib import Path

import pytest

pytest.importorskip("networkx")

from mikeio1d import Res1D
from mikeio1d.network import Network

_TESTDATA = Path(__file__).parent / "testdata"
_RIVER = str(_TESTDATA / "network_river.res1d")

# The only fixture whose reaches carry a river chainage rather than a per-link
# offset: 'river' covers km 53.1-55.1 of its branch, 'tributary' starts 50 m in,
# and 'basin_right' starts 10 m below its branch's zero.
_OFFSET_REACHES = ["river", "tributary", "basin_right"]

_EVERY_FIXTURE = [
    "network.res1d",  # urban links, each measured from its own zero
    "network_river.res1d",  # river branches, chainage along the branch
    "network_cali.res11",
    "epanet.res",  # link-node, no chainage at all
]


@pytest.fixture(scope="module")
def river():
    return Network.open(_RIVER)


@pytest.fixture(scope="module")
def river_lengths():
    """Reach lengths as Res1D reports them, which the graph must add up to."""
    return {name: reach.length for name, reach in Res1D(_RIVER).reaches.items()}


def _chain_nodes(network, reach_id):
    """A reach's graph nodes in order: start node, its breakpoints, end node.

    A breakpoint's address names the reach it belongs to, so one reach's chain
    can be read off the graph without asking the network for its reaches.
    """
    addresses = dict(network.to_networkx().nodes(data="address"))
    breakpoints = sorted(
        (address[1], node)
        for node, address in addresses.items()
        if isinstance(address, tuple) and address[0] == reach_id
    )
    by_address = {address: node for node, address in addresses.items()}
    reach = network.reaches[reach_id]
    return [
        by_address[reach.start],
        *(node for _, node in breakpoints),
        by_address[reach.end],
    ]


def _end_edges(network, reach_id):
    """The two edges joining a reach's own nodes to its outermost breakpoints."""
    chain = _chain_nodes(network, reach_id)
    graph = network.to_networkx()
    return graph.edges[chain[0], chain[1]], graph.edges[chain[-2], chain[-1]]


def _chain_lengths(network, reach_id):
    """Every edge length along one reach, start node through to end node."""
    chain = _chain_nodes(network, reach_id)
    graph = network.to_networkx()
    return [graph.edges[a, b]["length"] for a, b in zip(chain, chain[1:])]


class TestAReachThatDoesNotStartAtZero:
    """Its chainages are coordinates along a branch, not distances along itself."""

    @pytest.mark.parametrize("reach_id", _OFFSET_REACHES)
    def test_its_outermost_gridpoints_are_boundary_edges(self, river, reach_id):
        """A MIKE reach's first and last gridpoint sit on the reach's own ends."""
        leading, trailing = _end_edges(river, reach_id)

        assert (leading["length"], leading["boundary"]) == (0.0, True)
        assert (trailing["length"], trailing["boundary"]) == (0.0, True)

    @pytest.mark.parametrize("reach_id", _OFFSET_REACHES)
    def test_its_edges_add_up_to_its_length(self, river, river_lengths, reach_id):
        """The origin cancels, so the chain measures the reach and not the branch."""
        expected = river_lengths[reach_id]

        assert sum(_chain_lengths(river, reach_id)) == pytest.approx(expected)

    def test_a_breakpoint_below_its_branch_zero_keeps_its_sign(self, river):
        """A position can sit below its frame's origin, where a size cannot.

        'basin_right' is modelled 10 m upstream of its branch's chainage zero,
        so its first two breakpoints are negative. Reading their position as
        a size - the old ``abs(distance)`` - put them 10 m and 5 m from a start
        node they in fact sit on.
        """
        found = [river.resolve(("basin_right", d)).address for d in (-10.0, -5.0)]

        assert found == [("basin_right", -10.0), ("basin_right", -5.0)]


class TestEveryFixture:
    """What holds for a river network holds for the rest."""

    @pytest.mark.parametrize("filename", _EVERY_FIXTURE)
    def test_no_edge_has_a_negative_length(self, filename):
        """A negative length is a chainage read in the wrong frame."""
        graph = Network.open(str(_TESTDATA / filename)).to_networkx()

        lengths = [attrs["length"] for _, _, attrs in graph.edges(data=True)]

        assert [length for length in lengths if length is not None and length < 0] == []
