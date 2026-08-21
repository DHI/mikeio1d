"""Test how a network is opened: what it accepts, and what it reads alongside."""

# ruff: noqa: E402
import shutil
from pathlib import Path

import pytest

pytest.importorskip("networkx")

from mikeio1d import Res1D
from mikeio1d.network import Network
from mikeio1d.network._policy import _NETWORK_EXTENSIONS, _UNSUPPORTED_EXTENSIONS

_TESTDATA = Path(__file__).parent / "testdata"
_RES1D = str(_TESTDATA / "network.res1d")
_EPANET_RES = str(_TESTDATA / "epanet.res")
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
    return {reach_id: reach.length for reach_id, reach in network._reaches.items()}


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

    def test_every_extension_res1d_reads_is_accounted_for(self):
        """A format Res1D gains must be mapped or explicitly declined."""
        assert _NETWORK_EXTENSIONS | set(_UNSUPPORTED_EXTENSIONS) == (
            Res1D.get_supported_file_extensions()
        )

    def test_a_companion_result_points_at_the_file_that_holds_the_network(self):
        with pytest.raises(NotImplementedError, match="companions="):
            Network.open(str(_TESTDATA / "epanet.resx"))

    def test_a_format_without_topology_keeps_its_reason(self):
        with pytest.raises(NotImplementedError, match="companion '.inp' input file"):
            Network.open(str(_TESTDATA / "swmm.out"))

    def test_a_format_res1d_cannot_read_is_refused(self):
        with pytest.raises(NotImplementedError, match="Unsupported file extension"):
            Network.open(str(_TESTDATA / "xsections.xns11"))


def test_pumps_keep_an_unknown_length_even_with_the_inp(tmp_path):
    """[PIPES] is the only section carrying lengths."""
    res = _copy(tmp_path, "epanet", ".res", ".inp")

    lengths = _lengths(Network.open(res))

    assert lengths[_PUMP] is None
    assert sum(length is None for length in lengths.values()) == 1
