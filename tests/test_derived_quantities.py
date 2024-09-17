import pytest

import pandas as pd

from pandas.testing import assert_frame_equal


def test_access_available_derived_quantities(res1d_network):
    dq = res1d_network.derived_quantities
    assert len(dq) > 0
    assert None not in dq
    assert isinstance(dq[0], str)
    assert "NodeFlooding" in res1d_network.derived_quantities


def test_available_derived_quantities_by_locations(res1d_network):
    assert "NodeFlooding" in res1d_network.nodes.derived_quantities
    assert "NodeFlooding" not in res1d_network.reaches.derived_quantities


def test_available_derived_quantities_by_single_location(res1d_network):
    assert "NodeFlooding" in res1d_network.nodes["1"].derived_quantities
    assert "NodeFlooding" not in res1d_network.reaches["100l1"].derived_quantities


def test_read_derived_quantities_locations(res1d_network):
    df = res1d_network.nodes.NodeFlooding.read()
    assert df is not None
    assert len(df) > 0
    assert len(df.columns) > 1
    assert (df.columns.get_level_values("quantity") == "NodeFlooding").all()


def test_read_derived_quantities_single_location(res1d_network):
    df = res1d_network.nodes["1"].NodeFlooding.read()
    assert df is not None
    assert len(df) > 0
    assert len(df.columns) == 1
    assert (df.columns.get_level_values("quantity") == "NodeFlooding").all()


def set_multiindex_level_values(df, level, value):
    """Set all values of a MultiIndex level to a specific value."""
    num_columns = df.shape[1]
    df.columns = df.columns.set_levels([value for _ in range(num_columns)], level=level)
    return df


class TestSpecificDerivedQuantities:
    def test_node_flooding(self, res1d_network):
        node = res1d_network.nodes["1"]

        # Calculate expected values
        df_water_level = node.WaterLevel.read(column_mode="all")
        df_node_flooding_expected = df_water_level - node.ground_level
        set_multiindex_level_values(df_node_flooding_expected, "quantity", "NodeFlooding")
        set_multiindex_level_values(df_node_flooding_expected, "derived", True)
        df_node_flooding_expected.m1d.compact()
        df_node_flooding_expected = df_node_flooding_expected.droplevel("derived", axis=1)

        # Read derived values
        df_node_flooding = node.NodeFlooding.read()

        assert_frame_equal(df_node_flooding, df_node_flooding_expected)

    def test_node_depth(self, res1d_network):
        node = res1d_network.nodes["1"]

        # Calculate expected values
        df_water_level = node.WaterLevel.read(column_mode="all")
        df_node_depth_expected = df_water_level - node.bottom_level
        set_multiindex_level_values(df_node_depth_expected, "quantity", "NodeWaterDepth")
        set_multiindex_level_values(df_node_depth_expected, "derived", True)
        df_node_depth_expected.m1d.compact()
        df_node_depth_expected = df_node_depth_expected.droplevel("derived", axis=1)

        # Read derived values
        df_node_depth = node.NodeWaterDepth.read()

        assert_frame_equal(df_node_depth, df_node_depth_expected)
