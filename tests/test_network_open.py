"""Test how a network is opened: what it accepts, and what it reads alongside."""

# ruff: noqa: E402
import shutil
from pathlib import Path

import pytest

pytest.importorskip("networkx")

from mikeio1d import Res1D
from mikeio1d.network import Network
from mikeio1d.network._companions import _refuse_clashes, _rekey_by_main_file
from mikeio1d.network._inp import read_pipe_lengths

_TESTDATA = Path(__file__).parent / "testdata"
_RES1D = str(_TESTDATA / "network.res1d")
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

        assert from_str.graph.number_of_nodes() == from_path.graph.number_of_nodes()

    def test_a_res1d_opened_with_a_path_is_read(self):
        """Res1D documents a Path file_path, so a network has to cope with one."""
        network = Network.open(Res1D(Path(_RES1D)))

        assert network.graph.number_of_nodes() == Network.open(_RES1D).graph.number_of_nodes()

    def test_anything_else_is_a_type_error(self):
        with pytest.raises(TypeError, match="str, Path or Res1D"):
            Network.open(42)


class TestCompanionDiscovery:
    """Left alone, a load picks up the companions beside the result file."""

    def test_both_companions_are_found(self, tmp_path):
        res = _copy(tmp_path, "epanet", ".res", ".resx", ".inp")

        network = Network.open(res)

        assert _lengths(network)[_PIPE] == pytest.approx(_PIPE_LENGTH)
        assert "Volume" in network.quantities

    def test_the_graph_carries_the_length_read_from_the_inp(self, tmp_path):
        """A link-node reach's two break points sit one reach length apart."""
        network = Network.open(_copy(tmp_path, "epanet", ".res", ".inp"))
        start = network.resolve((_PIPE, 0.0)).node
        end = network.resolve((_PIPE, _PIPE_LENGTH)).node

        assert network.graph.edges[start, end]["length"] == pytest.approx(_PIPE_LENGTH)

    def test_an_empty_list_refuses_them(self, tmp_path):
        res = _copy(tmp_path, "epanet", ".res", ".resx", ".inp")

        network = Network.open(res, companions=[])

        assert _lengths(network)[_PIPE] is None
        assert "Volume" not in network.quantities

    def test_a_named_companion_need_not_be_a_sibling(self, tmp_path):
        res = _copy(tmp_path, "epanet", ".res")
        elsewhere = tmp_path / "elsewhere.inp"
        shutil.copy(_TESTDATA / "epanet.inp", elsewhere)

        network = Network.open(res, companions=[elsewhere])

        assert _lengths(network)[_PIPE] == pytest.approx(_PIPE_LENGTH)

    def test_an_opened_companion_is_accepted(self, tmp_path):
        res = _copy(tmp_path, "epanet", ".res", ".resx")

        network = Network.open(res, companions=[Res1D(str(tmp_path / "model.resx"))])

        assert "Volume" in network.quantities

    def test_a_mike_result_ignores_an_inp_beside_it(self, tmp_path):
        """Only EPANET writes companions this reader knows.

        A ``.res1d`` sharing a folder and stem with somebody else's EPANET input
        would otherwise take its reach lengths from another model.
        """
        res = _copy(tmp_path, "network", ".res1d")
        shutil.copy(_TESTDATA / "epanet.inp", tmp_path / "model.inp")

        assert _lengths(Network.open(res)) == _lengths(Network.open(_RES1D))


class TestCompanionErrors:
    """A companion that cannot be used says so, and says which file it was."""

    def test_an_unknown_extension_is_refused(self):
        with pytest.raises(ValueError, match="not a companion"):
            Network.open(_EPANET_RES, companions=[_RES1D])

    def test_two_of_a_kind_are_refused(self):
        inp = str(_TESTDATA / "epanet.inp")

        with pytest.raises(ValueError, match="Two '.inp' companions"):
            Network.open(_EPANET_RES, companions=[inp, inp])

    def test_an_opened_result_that_is_not_a_companion_is_refused(self):
        with pytest.raises(ValueError, match="not a companion"):
            Network.open(_EPANET_RES, companions=[Res1D(_EPANET_RES)])

    def test_a_found_companion_is_named_when_it_fails(self, tmp_path):
        res = _copy(tmp_path, "epanet", ".res")
        (tmp_path / "model.inp").write_text("[JUNCTIONS]\n", encoding="utf-8")

        with pytest.raises(ValueError, match="model.inp") as excinfo:
            Network.open(res)

        assert "companions=[]" in str(excinfo.value)

    def test_a_named_companion_is_left_to_speak_for_itself(self, tmp_path):
        """Nothing to explain when the caller chose the file."""
        res = _copy(tmp_path, "epanet", ".res")
        bad = tmp_path / "elsewhere.inp"
        bad.write_text("[JUNCTIONS]\n", encoding="utf-8")

        with pytest.raises(ValueError, match="no .PIPES. section"):
            Network.open(res, companions=[bad])


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
        with pytest.raises(NotImplementedError, match="companion '.inp' input file"):
            Network.open(str(_TESTDATA / "swmm.out"))

    def test_a_format_res1d_cannot_read_is_refused(self):
        with pytest.raises(NotImplementedError, match="Unsupported file extension"):
            Network.open(str(_TESTDATA / "xsections.xns11"))


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


def test_pumps_keep_an_unknown_length_even_with_the_inp(tmp_path):
    """[PIPES] is the only section carrying lengths."""
    res = _copy(tmp_path, "epanet", ".res", ".inp")

    lengths = _lengths(Network.open(res))

    assert lengths[_PUMP] is None
    assert sum(length is None for length in lengths.values()) == 1


def test_a_pipe_the_inp_gives_no_length_for_has_one_break_point(tmp_path):
    """A zero in [PIPES] says the length is unknown, not that the pipe has none.

    Taken as a real length it would place the reach's second break point at
    distance 0.0, on top of the first, and the two would share one key: the
    graph would get a zero-length self-loop, one edge more than the count
    test_network_breakpoints.py checks.
    """
    res = _copy(tmp_path, "epanet", ".res", ".inp")
    inp = tmp_path / "model.inp"
    inp.write_text(
        inp.read_text(encoding="latin-1").replace("3209.544", "0.000"), encoding="latin-1"
    )

    network = Network.open(res)
    aliases = [network.graph.nodes[node]["address"] for node in network.graph.nodes]

    assert _lengths(network)[_PIPE] is None
    assert [alias for alias in aliases if isinstance(alias, tuple) and alias[0] == _PIPE] == [
        (_PIPE, 0.0),
    ]


_NON_ASCII_INP = """
[PIPES]
rør1 1 2 250 300 100
"""
"""One pipe, named outside ASCII. Fields are whitespace-delimited either way."""


def _carrying(*quantities):
    """What a node or gridpoint carries, as a header describes it."""
    return dict.fromkeys(quantities)


class TestWhatNoFixtureCanReach:
    """Behaviour no fixture can reach through Network.open, so tested inside.

    Move a test out to the surface once a fixture can reach it, and add nothing
    here that a fixture already can.
    """

    def test_an_inp_in_the_codepage_epanet_writes_is_read_as_itself(self, tmp_path):
        """A non-ASCII reach id survives the '.inp'.

        EPANET writes its input file in the Windows ANSI codepage, while mikeio1d
        hands back '.res' names decoded as UTF-8, so one model can spell one reach
        two ways. Every fixture is pure ASCII, where the two spellings coincide.
        """
        inp = tmp_path / "model.inp"
        inp.write_bytes(_NON_ASCII_INP.encode("cp1252"))

        assert read_pipe_lengths(inp) == {"rør1": 250.0}

    def test_a_utf8_inp_is_reconciled_against_the_result(self, tmp_path):
        """Read one byte at a time, UTF-8 arrives mis-spelled - and repairable."""
        inp = tmp_path / "model.inp"
        inp.write_bytes(_NON_ASCII_INP.encode("utf-8"))

        lengths = read_pipe_lengths(inp)

        assert lengths != {"rør1": 250.0}
        assert _rekey_by_main_file(lengths, {"rør1"}) == {"rør1": 250.0}

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
