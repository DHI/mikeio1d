"""Test reading series from a network after the open, rather than during it.

Topology is cheap and series are not, so a network answers where a quantity
lives from the file header and its own break points, and reads only what it is
then asked for. The point of the split is when absence is discovered: a location
that carries nothing is an answer while the file is still open, not a reload.
"""

# ruff: noqa: E402
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

nx = pytest.importorskip("networkx")
pytest.importorskip("xarray")

from mikeio1d import Res1D
from mikeio1d.network import Network

_TESTDATA = Path(__file__).parent / "testdata"
_RES1D = str(_TESTDATA / "network.res1d")
_RIVER = str(_TESTDATA / "network_river.res1d")
_RES11 = str(_TESTDATA / "network_cali.res11")
_EPANET_RES = str(_TESTDATA / "epanet.res")

# The break point of 100l1 that carries discharge, and the reach's own length.
_Q_POINT = ("100l1", 23.8413574216414)
_PIPE_LENGTH = 3209.544


@pytest.fixture(scope="module")
def network():
    """A network as opened: its topology, and none of its series read."""
    return Network.open(_RES1D)


@pytest.fixture(scope="module")
def epanet():
    """EPANET, whose companions bring both extra quantities and reach lengths."""
    return Network.open(_EPANET_RES)


@pytest.fixture(scope="module")
def river():
    """A MIKE river result, whose header declares more than its network holds."""
    return Network.open(_RIVER)


class TestTheOpenReadsNothing:
    """The claim the whole surface rests on: metadata costs no timeseries."""

    def test_the_whole_metadata_surface_leaves_the_file_unread(self):
        res = Res1D(_RES1D)
        network = Network.open(res)

        _ = network.period
        dict(network.quantities)
        network.resolve("101")
        network.locations(quantity="Discharge")

        assert res.reader._loaded is False

    def test_opening_with_a_companion_result_leaves_both_files_unread(self):
        res = Res1D(_EPANET_RES)
        resx = Res1D(str(_TESTDATA / "epanet.resx"))

        Network.open(res, companions=[resx])

        assert res.reader._loaded is False
        assert resx.reader._loaded is False

    def test_a_read_leaves_the_opened_file_unread_too(self):
        """A read opens the file again for just what it asks for."""
        res = Res1D(_RES1D)
        network = Network.open(res)

        network.read([("101", "WaterLevel")])

        assert res.reader._loaded is False


class TestThePeriod:
    """First and last timestep, off the header."""

    def test_it_agrees_with_the_result_file(self, network):
        res = Res1D(_RES1D)

        assert network.period == (res.start_time, res.end_time)


class TestWhatQuantitiesMeans:
    """What can be read somewhere, against what this load happened to keep."""

    def test_a_quantity_carries_its_unit(self, network):
        assert network.quantities["Discharge"] == "m^3/s"

    def test_a_companion_quantity_carries_its_unit(self, epanet):
        """A quantity the main file never declares still knows what it is in.

        Tank volume is read from the '.resx', so its unit has to come from
        there too - the '.res' header has nothing to say about it.
        """
        assert epanet.quantities["Volume"] == "m^3"

    def test_it_names_what_the_network_carries(self, network):
        assert set(network.quantities) == {"WaterLevel", "Discharge"}

    def test_a_header_quantity_no_location_carries_is_left_out(self, river):
        """A river result keeps sensor and structure quantities off the network.

        Nothing in a network can address them, so advertising them would leave
        read() refusing what quantities had just offered.
        """
        declared = {str(q.Id) for q in Res1D(_RIVER).result_data.Quantities}

        assert "Discharge:Sensor:SensorGauge1" in declared
        assert "Discharge:Sensor:SensorGauge1" not in river.quantities

    def test_everything_offered_is_readable_somewhere(self, river):
        somewhere = {
            quantity
            for address in river.locations()
            for quantity in river.resolve(address).quantities
        }

        assert set(river.quantities) == somewhere

    def test_a_companion_contributes_its_own_quantities(self, epanet):
        """Volume is in the .resx, not in the .res the network was opened from."""
        assert "Volume" in epanet.quantities


class TestResolvingAnAddress:
    """The one lookup by name: whether a location is here, what it carries, and where."""

    def test_a_node_gives_back_its_own_name(self, network):
        resolved = network.resolve("101")

        assert (resolved.address, resolved.quantities) == ("101", ("WaterLevel",))

    def test_the_node_is_the_graph_integer_labelled_with_the_address(self, network):
        resolved = network.resolve(("100l1", 23.8), distance_tol=0.1)

        assert network.graph.nodes[resolved.node]["alias"] == resolved.address

    def test_the_node_selects_the_location_in_the_dataset(self, network):
        """The integer is what to_dataset() is indexed by, and names the same place."""
        node = network.resolve("101").node

        column = network.to_dataset()["WaterLevel"].sel(node=node)

        assert str(column["name"].item()) == "101"

    def test_a_break_point_snaps_to_the_distance_the_file_stores(self, network):
        resolved = network.resolve(("100l1", 23.8), distance_tol=0.1)

        assert resolved.address == _Q_POINT

    def test_a_distance_outside_the_tolerance_is_not_here(self, network):
        assert network.resolve(("100l1", 23.8)) is None

    def test_an_unknown_name_is_answered_rather_than_raised(self, network):
        """What makes resolve() usable for deciding whether to read at all."""
        assert network.resolve("no_such_node") is None

    def test_the_nearest_break_point_in_a_wide_window_wins(self, network):
        """A caller widening the window is snapping a measurement, not sweeping."""
        resolved = network.resolve(("100l1", 20.0), distance_tol=30.0)

        assert resolved.address == _Q_POINT

    @pytest.mark.parametrize("distance_tol", [-1.0, float("nan"), float("inf")])
    def test_a_tolerance_that_is_not_a_distance_is_refused(self, network, distance_tol):
        with pytest.raises(ValueError, match="finite, non-negative"):
            network.resolve(("100l1", 23.8), distance_tol=distance_tol)

    def test_a_location_carrying_nothing_still_resolves(self):
        """MIKE 11 keeps its timeseries on gridpoints, so its nodes hold none.

        An empty list and None are different answers, and this is the case that
        makes the difference matter.
        """
        res11 = Network.open(_RES11)
        node = next(iter(res11.reaches.values())).start

        resolved = res11.resolve(node)

        assert (resolved.address, resolved.quantities) == (node, ())

    def test_a_node_and_a_reach_sharing_a_name_stay_apart(self, epanet):
        """EPANET names a junction 10 and a pipe 10. The shape says which."""
        assert epanet.resolve("10").address == "10"
        assert epanet.resolve(("10", 0.0)).address == ("10", 0.0)


class TestListingLocations:
    """Where a quantity is, from topology alone."""

    def test_every_listed_address_resolves(self, network):
        assert all(network.resolve(address) is not None for address in network.locations())

    def test_a_quantity_splits_the_network(self, network):
        water_level = network.locations(quantity="WaterLevel")
        discharge = network.locations(quantity="Discharge")

        assert len(water_level) == 366
        assert len(discharge) == 129
        assert not set(water_level) & set(discharge)

    def test_a_reach_gives_its_break_points_and_not_its_nodes(self, network):
        points = network.locations(reach="100l1")

        assert points == [("100l1", 0.0), _Q_POINT, ("100l1", 47.6827148432828)]

    def test_a_reach_carrying_nothing_for_a_quantity_is_empty(self, network):
        assert network.locations(reach="100l1", quantity="Volume") == []

    def test_a_pipe_without_a_length_has_only_its_near_break_point(self):
        """Without the .inp a pipe has no length, so there is no distance for its far end."""
        alone = Network.open(_EPANET_RES, companions=[])

        assert [point.id for point in alone.reaches["10"].breakpoints] == [("10", 0.0)]
        assert alone.locations(reach="10") == [("10", 0.0)]

    def test_both_break_points_are_listed_once_the_inp_gives_a_length(self, epanet):
        assert epanet.locations(reach="10") == [("10", 0.0), ("10", _PIPE_LENGTH)]

    def test_a_reach_that_is_not_here_is_named(self, network):
        with pytest.raises(KeyError, match="no reach"):
            network.locations(reach="no_such_reach")


class TestReadingSeries:
    """The one member that touches data."""

    def test_a_series_matches_what_the_whole_frame_gives(self, network):
        """Reading one item gives what reading every item gives for it."""
        expected = network.to_dataframe()[("101", "WaterLevel")]

        read = network.read([("101", "WaterLevel")])

        assert np.allclose(read.iloc[:, 0].to_numpy(), expected.to_numpy())

    def test_a_mix_of_nodes_and_break_points_matches_the_result_file(self, network):
        """Nodes and gridpoints on several reaches, read in one call."""
        items = [
            ("101", "WaterLevel"),
            (_Q_POINT, "Discharge"),
            (("100l1", 0.0), "WaterLevel"),
            (network.locations(quantity="Discharge")[-1], "Discharge"),
        ]
        res = Res1D(_RES1D)
        expected = res.read(
            [
                res.nodes["101"].WaterLevel.timeseries_id,
                res.reaches["100l1"][1].Discharge.timeseries_id,
                res.reaches["100l1"][0].WaterLevel.timeseries_id,
            ],
            column_mode="timeseries",
        )

        read = network.read(items)

        assert np.allclose(read.iloc[:, :3].to_numpy(), expected.to_numpy())
        assert not read.iloc[:, 3].isna().any()

    def test_a_network_opened_from_a_res1d_reads_what_one_from_the_path_does(self, network):
        items = [("101", "WaterLevel"), (_Q_POINT, "Discharge")]

        read = Network.open(Res1D(_RES1D)).read(items)

        pd.testing.assert_frame_equal(read, network.read(items))

    def test_the_columns_are_the_items_that_were_asked_for(self, network):
        items = [("101", "WaterLevel"), (_Q_POINT, "Discharge")]

        read = network.read(items)

        assert list(read.columns) == items
        assert read[items[1]].shape == (110,)

    def test_a_measured_chainage_snaps_within_the_tolerance(self, network):
        """The column keeps the address asked for, so df[item] still finds it."""
        item = (("100l1", 23.8), "Discharge")
        expected = network.read([(_Q_POINT, "Discharge")]).iloc[:, 0]

        read = network.read([item], distance_tol=0.1)

        assert list(read.columns) == [item]
        assert np.allclose(read[item].to_numpy(), expected.to_numpy())

    def test_a_measured_chainage_outside_the_default_tolerance_is_refused(self, network):
        with pytest.raises(KeyError, match="distance_tol"):
            network.read([(("100l1", 23.8), "Discharge")])

    def test_a_tolerance_that_is_not_a_distance_is_refused(self, network):
        with pytest.raises(ValueError, match="finite, non-negative"):
            network.read([(("100l1", 23.8), "Discharge")], distance_tol=-1.0)

    def test_a_whole_reach_is_one_call(self, network):
        """A reach observation needs every break point, compared over the series."""
        points = network.locations(reach="100l1", quantity="WaterLevel")

        read = network.read([(point, "WaterLevel") for point in points])

        assert read.shape == (110, len(points))

    def test_asking_for_nothing_reads_nothing(self):
        """Res1D.read([]) means read everything, which is the opposite of this."""
        res = Res1D(_RES1D)
        network = Network.open(res)

        read = network.read([])

        assert read.empty
        assert res.reader._loaded is False

    def test_a_companion_quantity_reads_alongside_a_main_one(self, epanet):
        """The two live in different files, so this spans both in one call."""
        read = epanet.read([("9", "Volume"), ("9", "Head")])

        assert read.shape[1] == 2
        assert not read.isna().all().any()

    def test_two_break_points_on_one_gridpoint_give_one_series_twice(self, epanet):
        items = [(("10", 0.0), "Flow"), (("10", _PIPE_LENGTH), "Flow")]

        read = epanet.read(items)

        assert list(read.columns) == items
        assert np.allclose(read.iloc[:, 0].to_numpy(), read.iloc[:, 1].to_numpy())

    def test_a_missing_location_names_what_is_near_it(self, network):
        with pytest.raises(KeyError, match="none named 'no_such_node'"):
            network.read([("no_such_node", "WaterLevel")])

    def test_a_location_lacking_the_quantity_says_what_it_has(self, network):
        with pytest.raises(KeyError, match=r"carries \['WaterLevel'\], not 'Discharge'"):
            network.read([("101", "Discharge")])

    def test_a_location_carrying_nothing_points_at_the_gridpoints(self):
        res11 = Network.open(_RES11)
        node = next(iter(res11.reaches.values())).start

        with pytest.raises(KeyError, match="carries no quantities of its own"):
            res11.read([(node, "Discharge")])

    def test_every_failing_item_is_named_at_once(self, network):
        """Fifty locations should cost one round trip, not fifty."""
        with pytest.raises(KeyError) as failure:
            network.read([("101", "Discharge"), ("no_such_node", "WaterLevel")])

        assert "cannot read 2 of the 2" in str(failure.value)


class TestTheGraph:
    """What the graph lets a caller do to it."""

    def test_it_cannot_be_edited_under_the_lookups(self, network):
        with pytest.raises(nx.NetworkXError, match="Frozen"):
            network.graph.add_node(-1)

    def test_a_copy_of_it_can(self, network):
        graph = network.graph.copy()

        graph.add_node(-1)

        assert -1 not in network.graph
