"""Test how a network is opened: what it accepts, and what it reads alongside."""

# ruff: noqa: E402
import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest

pytest.importorskip("networkx")

from mikeio1d import Res1D
from mikeio1d.network import Network
from mikeio1d.network import _companions
from mikeio1d.network._companions import _refuse_clashes, _rekey_by_main_file
from mikeio1d.network._loader import _refuse_or_warn_catchments
from mikeio1d.network._res1d import _load_res1d_network
from mikeio1d.network._results import _Results
from mikeio1d.network._results import _Series

_TESTDATA = Path(__file__).parent / "testdata"
_RES1D = str(_TESTDATA / "network.res1d")
_RIVER = str(_TESTDATA / "network_river.res1d")
_EPANET_RES = str(_TESTDATA / "epanet.res")
_EPANET_RESX = str(_TESTDATA / "epanet.resx")
_PIPE, _PUMP = "10", "9"
_PIPE_LENGTH = 3209.544


def _copy(tmp_path, stem, *suffixes):
    """Copy a fixture set into tmp_path under one stem, keeping some companions."""
    tmp_path = Path(tmp_path)
    tmp_path.mkdir(parents=True, exist_ok=True)
    for suffix in suffixes:
        shutil.copy(_TESTDATA / f"{stem}{suffix}", tmp_path / f"model{suffix}")
    return tmp_path / f"model{suffixes[0]}"


def _lengths(network):
    """Each reach's length, None where it is unknown."""
    return {reach_id: reach.length for reach_id, reach in network.reaches.items()}


class TestWhatOpenAccepts:
    """A path or an already-opened result, and nothing else."""

    def test_a_path_and_a_str_agree(self):
        from_str = Network.open(_RES1D)
        from_path = Network.open(Path(_RES1D))

        assert from_str.to_networkx().number_of_nodes() == from_path.to_networkx().number_of_nodes()

    def test_a_res1d_opened_with_a_path_is_read(self):
        """Res1D documents a Path file_path, so a network has to cope with one."""
        network = Network.open(Res1D(Path(_RES1D)))

        assert (
            network.to_networkx().number_of_nodes()
            == Network.open(_RES1D).to_networkx().number_of_nodes()
        )

    def test_anything_else_is_a_type_error(self):
        with pytest.raises(TypeError, match="str, Path or Res1D"):
            Network.open(42)


class TestAFilteredRes1D:
    """A filter decides which series a network carries, not what the network is."""

    def test_a_name_filter_keeps_the_whole_network(self):
        filtered = Network.open(Res1D(_RES1D, nodes=["1"], reaches=["100l1"]))

        assert (
            filtered.to_networkx().number_of_nodes()
            == Network.open(_RES1D).to_networkx().number_of_nodes()
        )

    def test_a_location_the_filter_leaves_out_carries_nothing(self):
        filtered = Network.open(Res1D(_RES1D, nodes=["1"], reaches=["100l1"]))

        assert filtered.resolve("100").quantities == ()
        assert filtered.resolve("1").quantities == ("WaterLevel",)
        assert filtered.addresses(quantity="Discharge") == [("100l1", 23.8413574216414)]

    def test_a_location_the_filter_keeps_reads_as_unfiltered(self):
        filtered = Network.open(Res1D(_RES1D, nodes=["1"], reaches=["100l1"]))
        items = [("1", "WaterLevel"), (("100l1", 23.8413574216414), "Discharge")]

        assert filtered.read(items).equals(Network.open(_RES1D).read(items))

    def test_a_quantity_filter_leaves_only_its_quantities(self):
        filtered = Network.open(Res1D(_RES1D, quantities=["WaterLevel"]))

        assert list(filtered.quantities) == ["WaterLevel"]

    @pytest.mark.parametrize(
        "time_filter", [{"time": slice("1994-08-07 17:00", None)}, {"step_every": 2}]
    )
    def test_a_time_filter_is_not_implemented(self, time_filter):
        with pytest.raises(NotImplementedError, match="time or step_every"):
            Network.open(Res1D(_RES1D, **time_filter))

    def test_a_time_filtered_companion_is_not_implemented(self):
        with pytest.raises(NotImplementedError, match="time or step_every"):
            Network.open(_EPANET_RES, companions=[Res1D(_EPANET_RESX, step_every=2)])


class TestCompanionDiscovery:
    """Left alone, a load picks up the companion beside the result file."""

    def test_the_resx_is_found(self, tmp_path):
        res = _copy(tmp_path, "epanet", ".res", ".resx")

        network = Network.open(res)

        assert "Volume" in network.quantities

    def test_an_empty_list_refuses_it(self, tmp_path):
        res = _copy(tmp_path, "epanet", ".res", ".resx")

        network = Network.open(res, companions=[])

        assert "Volume" not in network.quantities

    def test_a_named_companion_need_not_be_a_sibling(self, tmp_path):
        res = _copy(tmp_path, "epanet", ".res")
        elsewhere = tmp_path / "elsewhere.resx"
        shutil.copy(_TESTDATA / "epanet.resx", elsewhere)

        network = Network.open(res, companions=[elsewhere])

        assert "Volume" in network.quantities

    def test_an_opened_companion_is_accepted(self, tmp_path):
        res = _copy(tmp_path, "epanet", ".res", ".resx")

        network = Network.open(res, companions=[Res1D(str(tmp_path / "model.resx"))])

        assert "Volume" in network.quantities

    def test_an_inp_beside_the_result_is_not_read(self, tmp_path):
        """The '.res' carries the lengths, so an input file beside it is no companion."""
        res = _copy(tmp_path, "epanet", ".res")
        (tmp_path / "model.inp").write_text("[JUNCTIONS]\n", encoding="utf-8")

        network = Network.open(res)

        assert _lengths(network) == _lengths(Network.open(_EPANET_RES, companions=[]))

    def test_a_mike_result_ignores_a_resx_beside_it(self, tmp_path):
        """Only EPANET writes companions this reader knows.

        A ``.res1d`` sharing a folder and stem with somebody else's EPANET result
        would otherwise take on another model's series.
        """
        res = _copy(tmp_path, "network", ".res1d")
        shutil.copy(_TESTDATA / "epanet.resx", tmp_path / "model.resx")

        assert list(Network.open(res).quantities) == list(Network.open(_RES1D).quantities)


class TestLengths:
    """An EPANET reach's length comes from the '.res' itself."""

    def test_a_pipe_has_the_length_the_model_gave_it(self):
        """Stored as a float32, and given back as the model wrote it."""
        network = Network.open(_EPANET_RES, companions=[])

        assert network.reaches[_PIPE].length == _PIPE_LENGTH

    def test_the_graph_carries_it_between_the_pipe_ends(self):
        """A link-node reach's two breakpoints sit one reach length apart."""
        network = Network.open(_EPANET_RES, companions=[])
        start = network.resolve((_PIPE, 0.0)).graph_node
        end = network.resolve((_PIPE, _PIPE_LENGTH)).graph_node

        assert network.to_networkx().edges[start, end]["length"] == _PIPE_LENGTH

    def test_only_the_pump_has_none(self):
        lengths = _lengths(Network.open(_EPANET_RES, companions=[]))

        assert [reach for reach, length in lengths.items() if length is None] == [_PUMP]

    def test_a_reach_without_a_length_has_one_breakpoint(self):
        """Its far end has no position, so it is not given one at 0.0 as well.

        Two breakpoints at 0.0 would share one key: the graph would get a
        zero-length self-loop, one edge more than the count
        test_network_breakpoints.py checks.
        """
        network = Network.open(_EPANET_RES, companions=[])

        assert network.addresses(reach=_PUMP) == [(_PUMP, 0.0)]


class TestCompanionErrors:
    """A companion that cannot be used says so, and says which file it was."""

    def test_an_unknown_extension_is_refused(self):
        with pytest.raises(ValueError, match="not a companion"):
            Network.open(_EPANET_RES, companions=[_RES1D])

    def test_an_inp_is_refused(self):
        """It used to supply reach lengths, which the '.res' now does."""
        with pytest.raises(ValueError, match="no longer a companion") as excinfo:
            Network.open(_EPANET_RES, companions=[str(_TESTDATA / "epanet.inp")])

        assert "companions=[]" not in str(excinfo.value)

    def test_two_resx_are_refused(self):
        with pytest.raises(ValueError, match="Two '.resx' companions"):
            Network.open(_EPANET_RES, companions=[_EPANET_RESX, _EPANET_RESX])

    def test_an_opened_result_that_is_not_a_companion_is_refused(self):
        with pytest.raises(ValueError, match="not a companion"):
            Network.open(_EPANET_RES, companions=[Res1D(_EPANET_RES)])

    def test_a_found_companion_is_named_when_it_fails(self, tmp_path, monkeypatch):
        """Stubbed: the one '.resx' fixture belongs to the one '.res'."""

        def refuse(res, resx):
            raise ValueError("not from the same run")

        monkeypatch.setattr(_companions, "_open_companion_result", refuse)
        res = _copy(tmp_path, "epanet", ".res", ".resx")

        with pytest.raises(ValueError, match="model.resx") as excinfo:
            Network.open(res)

        assert "companions=[]" in str(excinfo.value)


class TestExtensionPolicy:
    """One table decides what a network can be built from."""

    def test_every_extension_res1d_reads_is_accounted_for(self, tmp_path):
        """A format Res1D gains must be mapped or explicitly declined.

        The extension is checked before the file is opened, so a path to nothing
        is enough: it fails either way, but never for want of a mapping.
        """
        for extension in sorted(Res1D.get_supported_file_extensions()):
            with pytest.raises(Exception) as excinfo:
                Network.open(tmp_path / f"missing{extension}")

            assert "no network mapping yet" not in str(excinfo.value), extension

    def test_a_companion_result_points_at_the_file_that_holds_the_network(self):
        with pytest.raises(NotImplementedError, match="companions="):
            Network.open(str(_TESTDATA / "epanet.resx"))

    def test_a_format_without_topology_keeps_its_reason(self):
        with pytest.raises(NotImplementedError, match="sibling '.inp' input file"):
            Network.open(str(_TESTDATA / "swmm.out"))

    def test_a_format_res1d_cannot_read_is_refused(self):
        with pytest.raises(NotImplementedError, match="Unsupported file extension"):
            Network.open(str(_TESTDATA / "xsections.xns11"))


class TestCatchments:
    """A catchment has no address in a network, so a network does not quietly drop it."""

    @pytest.mark.parametrize(
        "filename",
        [
            "catchments.res1d",
            "catchment_merge_a.res1d",
            "catchment_merge_b.res1d",
        ],
    )
    def test_a_result_holding_only_catchments_is_refused(self, filename):
        """Rather than opening as an empty network, which looks like a network."""
        with pytest.raises(NotImplementedError, match="catchments are not part of a network"):
            Network.open(str(_TESTDATA / filename))


class TestQuantityIdsThatAreNoIdentifiers:
    """A quantity is read by its MIKE ID, not by the attribute name mikeio1d gives it."""

    @pytest.fixture(scope="class")
    def read(self):
        """Read one ``(address, quantity)`` from EPANET with its .resx, and the .resx's own."""
        network = Network.open(_EPANET_RES, companions=[_EPANET_RESX])
        own = Res1D(_EPANET_RESX).read()

        def read(address, quantity, column):
            got = network.read([(address, quantity)]).iloc[:, 0]
            return got.to_numpy(), own[column].to_numpy()

        return read

    def test_a_node_quantity_whose_id_is_no_identifier_is_read(self, read):
        """A .resx tank carries both Volume and Volume Percentage."""
        got, expected = read("2", "Volume Percentage", "Volume Percentage:2")

        assert got == pytest.approx(expected)

    def test_a_reach_quantity_whose_id_is_no_identifier_is_read(self, read):
        """A .resx pump carries efficiency, energy and energy costs."""
        got, expected = read((_PUMP, 0.0), "Pump energy", f"Pump energy:{_PUMP}")

        assert got == pytest.approx(expected)

    def test_two_ids_sharing_a_prefix_stay_apart(self, read):
        """'Pump energy' must not also claim the 'Pump energy costs' series."""
        got, expected = read((_PUMP, 0.0), "Pump energy costs", f"Pump energy costs:{_PUMP}")

        assert got == pytest.approx(expected)


@pytest.fixture(scope="module")
def epanet_res():
    """The EPANET result a stub companion is checked against."""
    return Res1D(_EPANET_RES)


def _resx_like(res, **changes):
    """A stand-in for a '.resx' of the same run as res, but for what changes."""
    fields = {
        "start_time": res.start_time,
        "end_time": res.end_time,
        "nodes": dict.fromkeys(res.nodes),
        "reaches": dict.fromkeys(res.reaches),
    }
    return SimpleNamespace(**{**fields, **changes})


def _carrying(*quantities):
    """What a node or gridpoint carries, as a header describes it."""
    return dict.fromkeys(quantities)


class TestWhatNoFixtureCanReach:
    """Behaviour no fixture can reach through Network.open, so tested inside.

    Move a test out to the surface once a fixture can reach it, and add nothing
    here that a fixture already can.
    """

    def test_a_resx_name_decoded_with_the_codepage_is_rekeyed(self):
        """mikeio1d decodes '.res' names as UTF-8 and '.resx' names with the Windows
        ANSI codepage, so one model can spell one reach two ways. Every fixture is
        pure ASCII, where the two spellings coincide.
        """
        mis_decoded = "rør1".encode("utf-8").decode("cp1252")

        assert _rekey_by_main_file({mis_decoded: "x"}, {"rør1"}) == {"rør1": "x"}

    def test_a_companion_clash_names_the_node_and_the_quantity(self):
        """No pair of fixtures collides: epanet.res and epanet.resx are disjoint.

        Nor can a collision be staged, since a '.res' copied under a '.resx' name
        fails to load before anything is compared.
        """
        res = {"9": _carrying("Flow", "Volume")}
        companion = {"9": _carrying("Volume")}

        with pytest.raises(ValueError, match=r"'9'.*\['Volume'\]"):
            _refuse_clashes(res, companion)

    def test_a_companion_clash_names_the_reach_whose_gridpoint_clashes(self):
        res = {("9", 0): _carrying("Flow", "Energy")}
        companion = {("9", 0): _carrying("Energy")}

        with pytest.raises(ValueError, match=r"'9'.*\['Energy'\]"):
            _refuse_clashes(res, companion)

    def test_catchments_beside_a_network_are_left_out_with_a_warning(self):
        """No fixture holds both: every catchment fixture holds catchments alone."""
        res = SimpleNamespace(
            file_path="model.res1d",
            reaches={"r1": None},
            catchments={"c1": SimpleNamespace(quantities=["TotalRunOff"])},
        )

        with pytest.warns(UserWarning, match=r"1 catchment\(s\).*\['TotalRunOff'\]"):
            _refuse_or_warn_catchments(res)

    @pytest.mark.parametrize(
        "changes, message",
        [
            ({"end_time": "2099-01-01"}, "same period"),
            ({"nodes": {"ghost": None}}, r"holds nodes \['ghost'\]"),
            ({"reaches": {"ghost": None}}, r"holds reaches \['ghost'\]"),
        ],
        ids=["period", "node", "reach"],
    )
    def test_a_resx_from_another_run_is_refused(self, monkeypatch, epanet_res, changes, message):
        """The one '.resx' fixture belongs to the one '.res', so the others are stubs."""
        monkeypatch.setattr(_companions, "_as_res1d", lambda file: file)

        with pytest.raises(ValueError, match=message):
            _companions._open_companion_result(epanet_res, _resx_like(epanet_res, **changes))

    @pytest.mark.parametrize(
        "count, listed",
        [(1, r"'n0'\.$"), (12, r"'n9', \.\.\. and 2 more\.$")],
    )
    def test_a_node_no_reach_ends_at_is_left_out_with_a_warning(self, epanet_res, count, listed):
        """Every fixture's nodes all end some reach."""
        res = SimpleNamespace(
            file_path="model.res1d",
            nodes=dict.fromkeys(f"n{i}" for i in range(count)),
            reaches={},
            start_time=epanet_res.start_time,
            end_time=epanet_res.end_time,
        )

        with pytest.warns(UserWarning, match=rf"{count} node\(s\) of 'model.res1d'.*{listed}"):
            _load_res1d_network(res, series_by_key={}, units={})

    def test_two_files_on_different_time_axes_are_not_read_together(self):
        """A .resx on another axis but the same period would reach this; no fixture is one."""
        own = Res1D(_RES1D).nodes["101"].WaterLevel.timeseries_id
        other = Res1D(_RIVER).nodes["'basin_left1', 0"].WaterLevel.timeseries_id
        results = _Results(
            series={
                "101": {"WaterLevel": _Series(Path(_RES1D), own)},
                "basin": {"WaterLevel": _Series(Path(_RIVER), other)},
            },
            units={},
            period=(None, None),
        )

        with pytest.raises(ValueError, match="does not share a time axis"):
            results.read([("101", "WaterLevel"), ("basin", "WaterLevel")])
