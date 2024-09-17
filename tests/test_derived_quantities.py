import pytest

import pandas as pd
import numpy as np

from pandas.testing import assert_frame_equal

NODE_DERIVED_QUANTITIES = [
    "NodeFlooding",
    "NodeWaterDepth",
    "NodeWaterLevelAboveCritical",
]

REACH_DERIVED_QUANTITIES = [
    "ReachAbsoluteDischarge",
    "ReachFilling",
    "ReachFlooding",
    "ReachQQManning",
    "ReachWaterDepth",
    "ReachWaterLevelAboveCritical",
]


@pytest.fixture(params=NODE_DERIVED_QUANTITIES)
def node_derived_quantity_id(request):
    return request.param


@pytest.fixture(params=REACH_DERIVED_QUANTITIES)
def reach_derived_quantity_id(request):
    return request.param


def test_access_available_derived_quantities(res1d_network):
    dq = res1d_network.derived_quantities
    assert len(dq) > 0
    assert None not in dq
    assert isinstance(dq[0], str)


def test_access_available_derived_quantities_nodes(res1d_network, node_derived_quantity_id):
    assert node_derived_quantity_id in res1d_network.derived_quantities


def test_access_available_derived_quantities_reaches(res1d_network, reach_derived_quantity_id):
    assert reach_derived_quantity_id in res1d_network.derived_quantities


def test_available_derived_quantities_by_locations_nodes(res1d_network, node_derived_quantity_id):
    assert node_derived_quantity_id in res1d_network.nodes.derived_quantities
    assert node_derived_quantity_id not in res1d_network.reaches.derived_quantities


def test_available_derived_quantities_by_locations_reaches(
    res1d_network, reach_derived_quantity_id
):
    assert reach_derived_quantity_id in res1d_network.reaches.derived_quantities
    assert reach_derived_quantity_id not in res1d_network.nodes.derived_quantities


def test_available_derived_quantities_by_single_location_node(
    res1d_network, node_derived_quantity_id
):
    assert node_derived_quantity_id in res1d_network.nodes["1"].derived_quantities
    assert node_derived_quantity_id not in res1d_network.reaches["100l1"].derived_quantities


def test_available_Derived_quantities_by_single_location_reach(
    res1d_network, reach_derived_quantity_id
):
    assert reach_derived_quantity_id in res1d_network.reaches["100l1"].derived_quantities
    assert reach_derived_quantity_id not in res1d_network.nodes["1"].derived_quantities


def test_read_derived_quantities_locations_nodes(res1d_network, node_derived_quantity_id):
    derived_result_quantity = getattr(res1d_network.nodes, node_derived_quantity_id)
    df = derived_result_quantity.read()
    assert df is not None
    assert len(df) > 0
    assert len(df.columns) == len(res1d_network.nodes)
    assert (df.columns.get_level_values("quantity") == node_derived_quantity_id).all()


def test_read_derived_quantities_locations_reaches(res1d_network, reach_derived_quantity_id):
    derived_result_quantity = getattr(res1d_network.reaches, reach_derived_quantity_id)
    df = derived_result_quantity.read()
    assert df is not None
    assert len(df) > 0
    assert len(df.columns) >= len(res1d_network.reaches)
    assert (df.columns.get_level_values("quantity") == reach_derived_quantity_id).all()


def test_read_derived_quantities_single_location_node(res1d_network, node_derived_quantity_id):
    derived_result_quantity = getattr(res1d_network.nodes["1"], node_derived_quantity_id)
    df = derived_result_quantity.read()
    assert df is not None
    assert len(df) > 0
    assert len(df.columns) == 1
    assert (df.columns.get_level_values("quantity") == node_derived_quantity_id).all()


def test_read_derived_quantities_single_location_reach(res1d_network, reach_derived_quantity_id):
    derived_result_quantity = getattr(res1d_network.reaches["100l1"], reach_derived_quantity_id)
    df = derived_result_quantity.read()
    assert df is not None
    assert len(df) > 0
    assert len(df.columns) >= 1
    assert (df.columns.get_level_values("quantity") == reach_derived_quantity_id).all()


def set_multiindex_level_values(df, level, value):
    """Set all values of a MultiIndex level to a specific value."""
    num_columns = df.shape[1]
    df.columns = df.columns.set_levels([value for _ in range(num_columns)], level=level)
    return df


class TestSpecificDerivedQuantities:
    def test_node_flooding(self, res1d_network):
        df = res1d_network.nodes["1"].NodeFlooding.read()
        assert df.max().max() == pytest.approx(-1.4010, abs=1e-4)
        assert df.min().min() == pytest.approx(-2.0170, abs=1e-4)
        assert df.mean().mean() == pytest.approx(-1.8711, abs=1e-4)

    def test_node_depth(self, res1d_network):
        df = res1d_network.nodes["1"].NodeWaterDepth.read()
        assert df.max().max() == pytest.approx(0.6190, abs=1e-4)
        assert df.min().min() == pytest.approx(0.0030, abs=1e-4)
        assert df.mean().mean() == pytest.approx(0.1489, abs=1e-4)

    def test_node_water_level_above_critical(self, res1d_network):
        df = res1d_network.nodes["1"].NodeWaterLevelAboveCritical.read()

        # test file has no critical levels for nodes, need better test case
        assert df.max().max() == -np.inf
        assert df.min().min() == -np.inf
        assert df.mean().mean() == -np.inf
