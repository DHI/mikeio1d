"""Test reading series from a network after the open, rather than during it.

Topology is cheap and series are not, so a network answers where a quantity
lives from the file header and its own breakpoints, and reads only what it is
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

# The breakpoint of 100l1 that carries discharge, and the reach's own length.
_Q_POINT = ("100l1", 23.8413574216414)
_PIPE_LENGTH = 3209.544


def _unread(res):
    """Whether a Res1D has loaded no timeseries yet.

    Res1D has no public way to say so, and it is not this module's to change,
    so this is the one place that looks inside it.
    """
    return res.reader._loaded is False


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
        network.addresses(quantity="Discharge")

        assert _unread(res)

    def test_opening_with_a_companion_result_leaves_both_files_unread(self):
        res = Res1D(_EPANET_RES)
        resx = Res1D(str(_TESTDATA / "epanet.resx"))

        Network.open(res, companions=[resx])

        assert _unread(res)
        assert _unread(resx)

    def test_a_read_leaves_the_opened_file_unread_too(self):
        """A read opens the file again for just what it asks for."""
        res = Res1D(_RES1D)
        network = Network.open(res)

        network.read([("101", "WaterLevel")])

        assert _unread(res)


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
            for address in river.addresses()
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

    def test_the_graph_node_is_the_integer_labelled_with_the_address(self, network):
        resolved = network.resolve(("100l1", 23.8), position_tol=0.1)

        assert network.to_networkx().nodes[resolved.graph_node]["address"] == resolved.address

    def test_the_graph_node_selects_the_location_in_the_dataset(self, network):
        """The integer is what to_dataset() is indexed by, and names the same place."""
        graph_node = network.resolve("101").graph_node

        column = network.to_dataset()["WaterLevel"].sel(graph_node=graph_node)

        assert str(column["node_id"].item()) == "101"

    def test_a_breakpoint_snaps_to_the_position_the_file_stores(self, network):
        resolved = network.resolve(("100l1", 23.8), position_tol=0.1)

        assert resolved.address == _Q_POINT

    def test_a_position_outside_the_tolerance_is_not_here(self, network):
        assert network.resolve(("100l1", 23.8)) is None

    def test_an_unknown_name_is_answered_rather_than_raised(self, network):
        """What makes resolve() usable for deciding whether to read at all."""
        assert network.resolve("no_such_node") is None

    def test_the_nearest_breakpoint_in_a_wide_window_wins(self, network):
        """A caller widening the window is snapping a measurement, not sweeping."""
        resolved = network.resolve(("100l1", 20.0), position_tol=30.0)

        assert resolved.address == _Q_POINT

    @pytest.mark.parametrize("position_tol", [-1.0, float("nan"), float("inf")])
    def test_a_tolerance_that_is_not_a_distance_is_refused(self, network, position_tol):
        with pytest.raises(ValueError, match="finite, non-negative"):
            network.resolve(("100l1", 23.8), position_tol=position_tol)

    @pytest.mark.parametrize("address", ["101", _Q_POINT], ids=["node", "breakpoint"])
    def test_the_tolerance_is_checked_even_for_an_exact_hit(self, network, address):
        with pytest.raises(ValueError, match="finite, non-negative"):
            network.resolve(address, position_tol=-1.0)

    def test_an_exact_hit_gives_the_position_the_file_stores(self, network):
        """("100l1", 0) and ("100l1", 0.0) are the same key, but only one is the file's."""
        resolved = network.resolve(("100l1", 0))

        assert type(resolved.address[1]) is float

    def test_a_rounded_position_names_the_breakpoint_the_file_stores(self, network):
        resolved = network.resolve(("100l1", round(_Q_POINT[1], 4)))

        assert resolved.address == _Q_POINT

    def test_a_tolerance_below_the_default_does_not_narrow_it(self, network):
        resolved = network.resolve(("100l1", round(_Q_POINT[1], 4)), position_tol=0.0)

        assert resolved.address == _Q_POINT

    def test_a_quantity_snaps_past_a_nearer_breakpoint_lacking_it(self, network):
        """5.0 is nearest the water level point at 0.0; discharge sits at 23.84."""
        resolved = network.resolve(("100l1", 5.0), position_tol=30.0, quantity="Discharge")

        assert resolved.address == _Q_POINT

    def test_a_named_breakpoint_lacking_the_quantity_is_not_snapped_away(self, network):
        resolved = network.resolve(("100l1", 0.0), position_tol=30.0, quantity="Discharge")

        assert resolved is None

    def test_a_node_lacking_the_quantity_is_not_here(self, network):
        assert network.resolve("101", quantity="Discharge") is None

    def test_a_quantity_leaves_every_quantity_in_the_answer(self, epanet):
        resolved = epanet.resolve("9", quantity="Volume")

        assert set(resolved.quantities) > {"Volume"}

    @pytest.mark.parametrize(
        ("address", "quantity", "position_tol"),
        [
            ("101", "WaterLevel", None),
            ("101", "Discharge", None),
            (("100l1", 5.0), "Discharge", 30.0),
            (("100l1", 0.0), "Discharge", 30.0),
            (("100l1", 5.0), "Discharge", None),
            (("100l1", 5.0), "Volume", 30.0),
            (("no_such_reach", 5.0), "Discharge", 30.0),
        ],
    )
    def test_it_answers_exactly_when_read_would(self, network, address, quantity, position_tol):
        """resolve(..., quantity=) is the check a caller makes before reading."""
        resolved = network.resolve(address, position_tol=position_tol, quantity=quantity)
        try:
            network.read([(address, quantity)], position_tol=position_tol)
            readable = True
        except KeyError:
            readable = False

        assert (resolved is not None) == readable

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


class TestListingAddresses:
    """Where a quantity is, from topology alone."""

    def test_every_listed_address_resolves(self, network):
        assert all(network.resolve(address) is not None for address in network.addresses())

    def test_a_quantity_splits_the_network(self, network):
        water_level = network.addresses(quantity="WaterLevel")
        discharge = network.addresses(quantity="Discharge")

        assert len(water_level) == 366
        assert len(discharge) == 129
        assert not set(water_level) & set(discharge)

    def test_a_reach_gives_its_breakpoints_and_not_its_nodes(self, network):
        points = network.addresses(reach="100l1")

        assert points == [("100l1", 0.0), _Q_POINT, ("100l1", 47.6827148432828)]

    def test_a_reach_carrying_nothing_for_a_quantity_is_empty(self, network):
        assert network.addresses(reach="100l1", quantity="Volume") == []

    def test_a_pipe_without_a_length_has_only_its_near_breakpoint(self):
        """Without the .inp a pipe has no length, so there is no position for its far end."""
        alone = Network.open(_EPANET_RES, companions=[])

        assert alone.reaches["10"].breakpoints == (("10", 0.0),)
        assert alone.addresses(reach="10") == [("10", 0.0)]

    def test_both_breakpoints_are_listed_once_the_inp_gives_a_length(self, epanet):
        assert epanet.addresses(reach="10") == [("10", 0.0), ("10", _PIPE_LENGTH)]

    def test_a_reach_that_is_not_here_is_named(self, network):
        with pytest.raises(KeyError, match="no reach"):
            network.addresses(reach="no_such_reach")

    def test_a_bare_structure_id_points_at_its_prefixed_reach(self, network):
        """A structure's reach keeps its type prefix; Res1D.structures does not."""
        with pytest.raises(KeyError, match="did you mean 'Weir:119w1'"):
            network.addresses(reach="119w1")


class TestReadingSeries:
    """The one member that touches data."""

    def test_a_series_matches_what_the_whole_frame_gives(self, network):
        """Reading one item gives what reading every item gives for it."""
        expected = network.to_dataframe()[("101", "WaterLevel")]

        read = network.read([("101", "WaterLevel")])

        assert np.allclose(read.iloc[:, 0].to_numpy(), expected.to_numpy())

    def test_a_mix_of_nodes_and_breakpoints_matches_the_result_file(self, network):
        """Nodes and gridpoints on several reaches, read in one call."""
        items = [
            ("101", "WaterLevel"),
            (_Q_POINT, "Discharge"),
            (("100l1", 0.0), "WaterLevel"),
            (network.addresses(quantity="Discharge")[-1], "Discharge"),
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

        read = network.read([item], position_tol=0.1)

        assert list(read.columns) == [item]
        assert np.allclose(read[item].to_numpy(), expected.to_numpy())

    def test_a_measured_chainage_outside_the_default_tolerance_is_refused(self, network):
        with pytest.raises(KeyError, match="position_tol"):
            network.read([(("100l1", 23.8), "Discharge")])

    def test_a_tolerance_that_is_not_a_distance_is_refused(self, network):
        with pytest.raises(ValueError, match="finite, non-negative"):
            network.read([(("100l1", 23.8), "Discharge")], position_tol=-1.0)

    @pytest.mark.parametrize("items", [[("101", "WaterLevel")], []], ids=["exact hit", "no items"])
    def test_the_tolerance_is_checked_whatever_the_items(self, network, items):
        with pytest.raises(ValueError, match="finite, non-negative"):
            network.read(items, position_tol=-1.0)

    def test_a_measured_chainage_snaps_onto_the_quantity_it_asks_for(self, network):
        """The case the staggered grid makes: the nearest breakpoint lacks discharge."""
        expected = network.read([(_Q_POINT, "Discharge")]).iloc[:, 0]

        read = network.read([(("100l1", 5.0), "Discharge")], position_tol=30.0)

        assert np.allclose(read.iloc[:, 0].to_numpy(), expected.to_numpy())

    def test_a_whole_reach_is_one_call(self, network):
        """A reach observation needs every breakpoint, compared over the series."""
        points = network.addresses(reach="100l1", quantity="WaterLevel")

        read = network.read([(point, "WaterLevel") for point in points])

        assert read.shape == (110, len(points))

    def test_asking_for_nothing_reads_nothing(self):
        """Res1D.read([]) means read everything, which is the opposite of this."""
        res = Res1D(_RES1D)
        network = Network.open(res)

        read = network.read([])

        assert read.empty
        assert _unread(res)

    def test_a_companion_quantity_reads_alongside_a_main_one(self, epanet):
        """The two live in different files, so this spans both in one call."""
        read = epanet.read([("9", "Volume"), ("9", "Head")])

        assert read.shape[1] == 2
        assert not read.isna().all().any()

    def test_two_breakpoints_on_one_gridpoint_give_one_series_twice(self, epanet):
        items = [(("10", 0.0), "Flow"), (("10", _PIPE_LENGTH), "Flow")]

        read = epanet.read(items)

        assert list(read.columns) == items
        assert np.allclose(read.iloc[:, 0].to_numpy(), read.iloc[:, 1].to_numpy())

    def test_a_missing_location_names_what_is_near_it(self, network):
        with pytest.raises(KeyError, match="none named 'no_such_node'"):
            network.read([("no_such_node", "WaterLevel")])

    def test_the_far_end_of_a_pipe_without_a_length_says_why_it_is_missing(self):
        """Widening position_tol would snap the far end onto the near one."""
        alone = Network.open(_EPANET_RES, companions=[])

        with pytest.raises(KeyError, match="no known length.*however wide position_tol"):
            alone.read([(("10", _PIPE_LENGTH), "Flow")])

    def test_a_location_lacking_the_quantity_says_what_it_has(self, network):
        with pytest.raises(KeyError, match=r"carries \['WaterLevel'\], not 'Discharge'"):
            network.read([("101", "Discharge")])

    def test_a_named_breakpoint_lacking_the_quantity_says_where_it_is(self, network):
        with pytest.raises(
            KeyError, match="not snapped away from it. Nearest carrying 'Discharge': 23.8414"
        ):
            network.read([(("100l1", 0.0), "Discharge")], position_tol=30.0)

    def test_a_window_without_the_quantity_names_where_it_is(self, network):
        """The message is about the position asked for, not a breakpoint near it."""
        with pytest.raises(KeyError) as failure:
            network.read([(("100l1", 5.0), "Discharge")])

        message = str(failure.value)
        assert (
            "('100l1', 5.0) - no breakpoint carrying 'Discharge' within position_tol=0.001"
            in message
        )
        assert "nearest carrying it: 23.8414" in message
        assert "WaterLevel" not in message

    def test_a_reach_without_the_quantity_does_not_invite_a_wider_window(self, network):
        with pytest.raises(KeyError, match="reach '100l1' carries 'Volume' at no breakpoint"):
            network.read([(("100l1", 5.0), "Volume")], position_tol=30.0)

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


class TestReadingOneQuantity:
    """read(quantity=...) as the short form of listing a quantity's addresses."""

    def test_it_reads_what_the_listed_addresses_read(self, network):
        items = [(a, "Discharge") for a in network.addresses(quantity="Discharge")]

        pd.testing.assert_frame_equal(network.read(quantity="Discharge"), network.read(items))

    def test_a_quantity_carried_nowhere_is_refused_with_what_is_carried(self, network):
        with pytest.raises(KeyError, match="no location carrying 'Volume'.*WaterLevel"):
            network.read(quantity="Volume")

    def test_neither_items_nor_quantity_is_refused(self, network):
        with pytest.raises(TypeError, match="either items or quantity"):
            network.read()

    def test_both_items_and_quantity_are_refused(self, network):
        with pytest.raises(TypeError, match="either items or quantity"):
            network.read([("101", "WaterLevel")], quantity="WaterLevel")

    def test_a_tolerance_with_a_quantity_is_refused(self, network):
        with pytest.raises(TypeError, match="position_tol only with items"):
            network.read(quantity="Discharge", position_tol=0.1)


class TestTheGraph:
    """What the graph lets a caller do to it."""

    def test_editing_it_leaves_the_network_as_it_was(self, network):
        graph = network.to_networkx()

        graph.add_node(-1)

        assert -1 not in network.to_networkx()
