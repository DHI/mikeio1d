"""Test the shape of the answers ``find`` and ``recall`` give.

A caller who builds a selection programmatically has no way to know whether it
holds one name or several, so a list argument must be answered with a list
either way. Anything else breaks at exactly the n == 1 case: ``len()`` raises,
iterating walks the digits of an integer, and ``Dataset.sel`` drops the ``node``
dimension instead of keeping it length one.
"""

# ruff: noqa: E402
from pathlib import Path

import pytest

pytest.importorskip("networkx")
pytest.importorskip("xarray")

from mikeio1d.network import Network

_TESTDATA = Path(__file__).parent / "testdata"
_EPANET_RES = str(_TESTDATA / "epanet.res")
_EPANET_INP = str(_TESTDATA / "epanet.inp")


@pytest.fixture(scope="module")
def epanet():
    return Network.open(_EPANET_RES, companions=[_EPANET_INP])


class TestAListIsAnsweredWithAList:
    def test_one_node(self, epanet):
        assert epanet.find(node=["10"]) == [epanet.find(node="10")]

    def test_several_nodes(self, epanet):
        answer = epanet.find(node=["10", "11"])

        assert answer == [epanet.find(node="10"), epanet.find(node="11")]

    def test_one_distance(self, epanet):
        assert epanet.find(reach="10", distance=[0.0]) == [epanet.find(reach="10", distance=0.0)]

    def test_one_reach_endpoint(self, epanet):
        answer = epanet.find(reach="10", distance=["start"])

        assert answer == [epanet.find(reach="10", distance="start")]

    def test_one_id_recalled(self, epanet):
        node_id = epanet.find(node="10")

        assert epanet.recall([node_id]) == [epanet.recall(node_id)]


class TestAScalarIsAnsweredWithAScalar:
    def test_a_node(self, epanet):
        assert isinstance(epanet.find(node="10"), int)

    def test_a_distance(self, epanet):
        assert isinstance(epanet.find(reach="10", distance=0.0), int)

    def test_an_id_recalled(self, epanet):
        assert epanet.recall(epanet.find(node="10")) == {"node": "10"}
