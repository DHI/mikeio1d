import pytest

import pandas as pd
import numpy as np

from matplotlib.axes import Axes
from pandas.testing import assert_frame_equal

from mikeio1d import Res1D
from mikeio1d.quantities import DerivedQuantity
from mikeio1d.quantities import TimeSeriesIdGroup

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
    df.columns = df.columns.set_levels([value], level=level)
    return df


def test_custom_derived_quantity_invalid_name(res1d_network):
    with pytest.raises(ValueError):

        class CustomDerivedQuantity(DerivedQuantity):
            _NAME = 1
            _GROUPS = {TimeSeriesIdGroup.NODE}
            _SOURCE_QUANTITY = "WaterLevel"

            def derive(self, df_source, locations):
                return df_source

        CustomDerivedQuantity(res1d_network)


def test_custom_derived_quantity_invalid_group(res1d_network):
    with pytest.raises(ValueError):

        class CustomDerivedQuantity(DerivedQuantity):
            _NAME = "CustomDerivedQuantity"
            _GROUPS = TimeSeriesIdGroup.NODE
            _SOURCE_QUANTITY = "WaterLevel"

            def derive(self, df_source, locations):
                return df_source

        CustomDerivedQuantity(res1d_network)


def test_custom_derived_quantity_invalid_source(res1d_network):
    with pytest.raises(ValueError):

        class CustomDerivedQuantity(DerivedQuantity):
            _NAME = "CustomDerivedQuantity"
            _GROUPS = {TimeSeriesIdGroup.NODE}
            _SOURCE_QUANTITY = 2

            def derive(self, df_source, locations):
                return df_source

        CustomDerivedQuantity(res1d_network)


def test_custom_derived_quantity_basic(res1d_network):
    class CustomDerivedQuantity(DerivedQuantity):
        _NAME = "WaterLevel"
        _GROUPS = {TimeSeriesIdGroup.NODE}
        _SOURCE_QUANTITY = "WaterLevel"

        def derive(self, df_source, locations):
            return df_source

    df = CustomDerivedQuantity(res1d_network).generate(
        res1d_network.nodes.WaterLevel.read(column_mode="timeseries")
    )
    df.columns = df.columns.droplevel("derived")
    assert_frame_equal(df, res1d_network.nodes.WaterLevel.read(column_mode="compact"))


def test_custom_derived_quantity_example(res1d_network):
    from mikeio1d.quantities.derived.derived_quantity_example import ExampleDerivedQuantity
    from mikeio1d.res1d import derived_quantity_manager as dqm

    dqm.register(ExampleDerivedQuantity)
    res1d_network = Res1D(res1d_network.file_path)

    assert "WaterLevelPlusOne" in res1d_network.derived_quantities
    assert "WaterLevelPlusOne" in res1d_network.nodes.derived_quantities
    assert "WaterLevelPlusOne" in res1d_network.reaches.derived_quantities

    df_nodes = res1d_network.nodes.WaterLevelPlusOne.read()
    df_nodes_expected = res1d_network.nodes.WaterLevel.read(column_mode="compact") + 1
    df_nodes_expected = set_multiindex_level_values(
        df_nodes_expected, "quantity", "WaterLevelPlusOne"
    )
    assert_frame_equal(df_nodes, df_nodes_expected)

    df_reaches = res1d_network.reaches.WaterLevelPlusOne.read()
    df_reaches_expected = res1d_network.reaches.WaterLevel.read(column_mode="compact") + 1
    df_reaches_expected = set_multiindex_level_values(
        df_reaches_expected, "quantity", "WaterLevelPlusOne"
    )
    assert_frame_equal(df_reaches, df_reaches_expected)


def test_result_derived_quantity_plots(res1d_network):
    ax = res1d_network.nodes["1"].NodeFlooding.plot()
    assert isinstance(ax, Axes)
    assert ax.get_ylabel() == "NodeFlooding"

    ax = res1d_network.nodes.NodeFlooding.plot()
    assert isinstance(ax, Axes)
    assert ax.get_ylabel() == "NodeFlooding"


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

    def test_reach_flooding(self, res1d_network):
        df = res1d_network.reaches["84l1"].ReachFlooding.read()

        # (lower chainage bound, upper chainage bound, agg) : expected_value
        data = {
            (96, 97, "max"): -0.775863647460938,
            (48, 49, "max"): -0.532844543457031,
            (0, 1, "max"): -0.290130615234375,
            (96, 97, "min"): -3.42999267578125,
            (48, 49, "min"): -3.15599822998047,
            (0, 1, "min"): -2.87599182128906,
            (96, 97, "mean"): -2.83537195379084,
            (48, 49, "mean"): -2.6148774580522,
            (0, 1, "mean"): -2.38141729181463,
        }

        for (lower, upper, agg), expected_value in data.items():
            assert df.m1d.query(f"chainage.between({lower},{upper})").agg(agg).agg(
                agg
            ) == pytest.approx(expected_value, abs=1e-4)

    def test_reach_depth(self, res1d_network):
        df = res1d_network.reaches["84l1"].ReachWaterDepth.read()

        # (lower chainage bound, upper chainage bound, agg) : expected_value
        data = {
            (96, 97, "max"): 2.66413879394531,
            (48, 49, "max"): 2.62715148925781,
            (0, 1, "max"): 2.58985900878906,
            (96, 97, "min"): 0.010009765625,
            (48, 49, "min"): 0.003997802734375,
            (0, 1, "min"): 0.003997802734375,
            (96, 97, "mean"): 0.604630487615412,
            (48, 49, "mean"): 0.545118574662642,
            (0, 1, "mean"): 0.498572332208807,
        }

        for (lower, upper, agg), expected_value in data.items():
            assert df.m1d.query(f"chainage.between({lower},{upper})").agg(agg).agg(
                agg
            ) == pytest.approx(expected_value, abs=1e-4)

    def test_reach_water_level_above_critical(self, res1d_network):
        df = res1d_network.reaches["84l1"].ReachWaterLevelAboveCritical.read()

        # (lower chainage bound, upper chainage bound, agg) : expected_value
        data = {
            (96, 97, "max"): -0.775863647460938,
            (48, 49, "max"): -0.532844543457031,
            (0, 1, "max"): -0.290130615234375,
            (96, 97, "min"): -3.42999267578125,
            (48, 49, "min"): -3.15599822998047,
            (0, 1, "min"): -2.87599182128906,
            (96, 97, "mean"): -2.83537195379084,
            (48, 49, "mean"): -2.6148774580522,
            (0, 1, "mean"): -2.38141729181463,
        }

        for (lower, upper, agg), expected_value in data.items():
            assert df.m1d.query(f"chainage.between({lower},{upper})").agg(agg).agg(
                agg
            ) == pytest.approx(expected_value, abs=1e-4)

    def test_reach_filling(self, res1d_network):
        df = res1d_network.reaches["84l1"].ReachFilling.read()

        # (lower chainage bound, upper chainage bound, agg) : expected_value
        data = {
            (96, 97, "max"): 3.33017349243164,
            (48, 49, "max"): 3.28393936157227,
            (0, 1, "max"): 3.23732376098633,
            (96, 97, "min"): 0.01251220703125,
            (48, 49, "min"): 0.00499725341796875,
            (0, 1, "min"): 0.00499725341796875,
            (96, 97, "mean"): 0.755788109519265,
            (48, 49, "mean"): 0.681398218328303,
            (0, 1, "mean"): 0.623215415261009,
        }

        for (lower, upper, agg), expected_value in data.items():
            assert df.m1d.query(f"chainage.between({lower},{upper})").agg(agg).agg(
                agg
            ) == pytest.approx(expected_value, abs=1e-4)

    def test_reach_qq_manning(self, res1d_network):
        df = res1d_network.reaches["84l1"].ReachQQManning.read()

        # (lower chainage bound, upper chainage bound, agg) : expected_value
        data = {
            (24, 25, "max"): 0.899804353713989,
            (72, 73, "max"): 0.884586334228516,
            (24, 25, "min"): 6.45247928332537e-05,
            (72, 73, "min"): -0.00437665591016412,
            (24, 25, "mean"): 0.17750987808699,
            (72, 73, "mean"): 0.17502574035964,
        }

        for (lower, upper, agg), expected_value in data.items():
            assert df.m1d.query(f"chainage.between({lower},{upper})").agg(agg).agg(
                agg
            ) == pytest.approx(expected_value, abs=1e-4)
