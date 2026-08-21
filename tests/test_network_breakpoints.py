"""Test which of a reach's gridpoints become break points.

A MIKE reach brings its own gridpoints, and each one is a real, measured
position along the reach. A link-node reach (EPANET, SWMM) brings none, so
mikeio1d hands it one synthetic stand-in that belongs to neither end, and
that one point has to be placed at both ends by hand. The two cases are told
apart by what the file reported, never by how many gridpoints came back.
"""

# ruff: noqa: E402
from pathlib import Path

import pytest

pytest.importorskip("networkx")

from mikeio1d import Res1D
from mikeio1d.network._res1d import _build_reach_breakpoints
from mikeio1d.network._res1d import _has_real_gridpoints

_TESTDATA = Path(__file__).parent / "testdata"
_RIVER = str(_TESTDATA / "network_river.res1d")
_EPANET_RES = str(_TESTDATA / "epanet.res")


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


def _distances(reach, **kwargs):
    kwargs.setdefault("length", 100.0)
    kwargs.setdefault("quantities", None)
    kwargs.setdefault("populate_gridpoints", False)
    return [bp.distance for bp in _build_reach_breakpoints(reach, **kwargs)]


class TestAReachWithGridpointsOfItsOwn:
    """Every gridpoint is a measured position, so every one is kept."""

    def test_a_two_gridpoint_reach_keeps_both(self):
        """Both ends were measured, so neither may be dropped for the other.

        Nothing in the test data reports as few as two - a MIKE reach carries
        an h-point at each end with at least one Q-point between - but the
        count is the file's to choose, and reading it as a link-node reach
        would discard the end gridpoint and duplicate the start's data. The
        chainages here are a branch coordinate, as a river reach's are, so
        the two readings cannot agree by accident.
        """
        reach = _Reach("r0", [53100.0, 53200.0])

        assert _distances(reach) == [53100.0, 53200.0]

    def test_a_river_reach_keeps_one_break_point_per_gridpoint(self):
        """The real thing, at chainages along the branch rather than from zero."""
        reach = Res1D(_RIVER).reaches["river"]

        assert _distances(reach) == [gp.chainage for gp in reach.gridpoints]


class TestAReachWithNoGridpointsOfItsOwn:
    """Its one stand-in has to answer for both ends."""

    def test_its_stand_in_is_placed_at_each_end(self):
        reach = Res1D(_EPANET_RES).reaches["10"]

        assert _distances(reach, length=250.0) == [0.0, 250.0]

    def test_an_unknown_length_leaves_the_far_end_unplaced(self):
        """EPANET reports no length, and a guessed one would measure edges."""
        reach = Res1D(_EPANET_RES).reaches["10"]

        assert _distances(reach, length=None) == [0.0, None]


class TestWhatTellsTheTwoApart:
    """The file's own gridpoint count, not the count mikeio1d handed back."""

    def test_a_reach_that_reported_gridpoints_has_real_ones(self):
        assert _has_real_gridpoints(_Reach("r0", [0.0, 100.0])) is True

    def test_a_reach_that_reported_none_got_a_stand_in(self):
        link_node = _Reach("r0", [])
        link_node.gridpoints = [_Gridpoint("r0", 0.0)]

        assert _has_real_gridpoints(link_node) is False

    def test_every_river_reach_has_real_gridpoints(self):
        reaches = Res1D(_RIVER).reaches.values()

        assert all(_has_real_gridpoints(reach) for reach in reaches)

    def test_no_link_node_reach_does(self):
        reaches = Res1D(_EPANET_RES).reaches.values()

        assert not any(_has_real_gridpoints(reach) for reach in reaches)
