"""Test the dataset a network hands out, and the identity its coordinates carry."""

# ruff: noqa: E402
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

pytest.importorskip("networkx")
pytest.importorskip("xarray")

from mikeio1d.network import Network

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
        node_id = epanet.resolve("10")["node"]

        name, reach, distance = _by_int(epanet.to_dataset(), node_id)

        assert name == "10"
        assert reach == ""
        assert np.isnan(distance)

    def test_a_breakpoint_carries_its_reach_and_distance(self, epanet):
        node_id = epanet.resolve(("10", 0.0))["node"]

        name, reach, distance = _by_int(epanet.to_dataset(), node_id)

        assert name == ""
        assert reach == "10"
        assert distance == pytest.approx(0.0)

    def test_the_coordinates_agree_with_the_graph(self, epanet):
        """The graph's alias is the same answer, so the two must never drift apart."""
        ds = epanet.to_dataset()

        for node_id in ds.node.values:
            name, reach, distance = _by_int(ds, node_id)
            alias = epanet.graph.nodes[int(node_id)]["alias"]

            if isinstance(alias, str):
                assert (name, reach) == (alias, "")
                assert np.isnan(distance)
            else:
                assert (name, reach) == ("", alias[0])
                expected = alias[1]
                assert np.isnan(distance) if expected is None else distance == expected

    def test_a_quantity_keeps_its_long_name(self, epanet):
        ds = epanet.to_dataset()

        assert ds["Flow"].attrs["long_name"] == "Flow"

