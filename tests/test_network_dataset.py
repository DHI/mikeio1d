"""Test the dataset a network hands out, and the identity its coordinates carry."""

# ruff: noqa: E402
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

pytest.importorskip("networkx")
pytest.importorskip("xarray")

from mikeio1d.network import BasicNode, BasicReach, Network

_TESTDATA = Path(__file__).parent / "testdata"
_EPANET_RES = str(_TESTDATA / "epanet.res")
_EPANET_INP = str(_TESTDATA / "epanet.inp")


@pytest.fixture
def epanet():
    return Network.open(_EPANET_RES, companions=[_EPANET_INP])


def _by_int(ds, node_id):
    """Return the identity coordinates of one node, as plain Python values."""
    at = ds.sel(node=node_id)
    return str(at.name.values), str(at.reach.values), float(at.distance.values)


class TestIdentityCoordinates:
    """Every column says which location it came from, without the network."""

    def test_a_node_carries_its_name(self, epanet):
        node_id = epanet.find(node="10")

        name, reach, distance = _by_int(epanet.to_dataset(), node_id)

        assert name == "10"
        assert reach == ""
        assert np.isnan(distance)

    def test_a_breakpoint_carries_its_reach_and_distance(self, epanet):
        node_id = epanet.find(reach="10", distance=0.0)

        name, reach, distance = _by_int(epanet.to_dataset(), node_id)

        assert name == ""
        assert reach == "10"
        assert distance == pytest.approx(0.0)

    def test_the_coordinates_agree_with_recall(self, epanet):
        """recall is the same answer, so the two must never drift apart."""
        ds = epanet.to_dataset()

        for node_id in ds.node.values:
            name, reach, distance = _by_int(ds, node_id)
            recalled = epanet.recall(int(node_id))

            if "node" in recalled:
                assert (name, reach) == (recalled["node"], "")
                assert np.isnan(distance)
            else:
                assert (name, reach) == ("", recalled["reach"])
                expected = recalled["distance"]
                assert np.isnan(distance) if expected is None else distance == expected

    def test_a_quantity_keeps_its_long_name(self, epanet):
        ds = epanet.to_dataset()

        assert ds["Flow"].attrs["long_name"] == "Flow"


class TestWithoutAResultFile:
    """A network can be built by hand, and its dataset needs no MIKE file."""

    def test_a_hand_built_network_produces_the_same_coordinates(self):
        time = pd.date_range("2024-01-01", periods=3, freq="h")
        nodes = [
            BasicNode(name, pd.DataFrame({"WaterLevel": [1.0, 2.0, 3.0]}, index=time))
            for name in ("A", "B", "C")
        ]
        reaches = [
            BasicReach("r0", nodes[0], nodes[1], length=100.0),
            BasicReach("r1", nodes[1], nodes[2], length=50.0),
        ]

        ds = Network(reaches).to_dataset()

        assert sorted(str(name) for name in ds.name.values) == ["A", "B", "C"]
        assert set(str(reach) for reach in ds.reach.values) == {""}
        assert np.isnan(ds.distance.values).all()
        assert ds["WaterLevel"].sizes == {"time": 3, "node": 3}

    def test_a_network_holding_no_data_gives_an_empty_dataset(self):
        empty = pd.DataFrame()
        nodes = [BasicNode("A", empty), BasicNode("B", empty)]

        ds = Network([BasicReach("r0", nodes[0], nodes[1], length=1.0)]).to_dataset()

        assert len(ds.data_vars) == 0
