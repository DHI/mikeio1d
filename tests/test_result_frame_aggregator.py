import pytest

from mikeio1d.pandas_extension import ResultFrameAggregator

import random

import pandas as pd
from pandas.testing import assert_index_equal
import numpy as np
from numpy.testing import assert_array_equal


@pytest.fixture(params=["max", np.mean, ["max"]])
def agg(params):
    return params


@pytest.fixture()
def df_dummy():
    return create_dummy_dataframe()


@pytest.fixture()
def df_simple():
    return create_simple_dataframe()


def create_simple_dataframe() -> pd.DataFrame:
    tuples = [
        ("A", "B", "B"),
        ("A", "B", "A"),
        ("A", "A", "B"),
        ("A", "A", "A"),
    ]
    index = pd.MultiIndex.from_tuples(tuples, names=["LA", "LB", "LC"])
    values = [[col * 10 + row for col in range(2)] for row in range(4)]
    df = pd.DataFrame(values, index=index).T
    return df


def create_dummy_dataframe() -> pd.DataFrame:
    """
    Creates a dummy dataframe with N_ROW rows and N_COL columns.
    The data values are: value = N_ROW * 10 + N_COL
    """
    N_ROW = 3
    N_COL = 100
    level_names = ["quantity", "group", "name", "chainage", "tag", "duplicate", "derived"]
    tuples = []
    for _ in range(N_COL):
        quantity = random.choice(["A", "B", "C"])
        group = random.choice(["A", "B", "C"])
        name = random.choice(["A", "B", "C"])
        chainage = random.uniform(0, 100)
        tag = random.choice(["A", "B", "C"])
        duplicate = random.randint(0, 2)
        derived = bool(random.getrandbits(1))
        tuples.append((quantity, group, name, chainage, tag, duplicate, derived))

    index = pd.MultiIndex.from_tuples(tuples, names=level_names)
    values = [[col * 10 + row for col in range(N_ROW)] for row in range(N_COL)]
    df = pd.DataFrame(values, index=index).T
    return df


class TestResultFrameAggregatorUnit:
    def test_init(self):
        with pytest.raises(ValueError):
            ResultFrameAggregator()

        ResultFrameAggregator("max")
        ResultFrameAggregator(np.mean)
        ResultFrameAggregator("max", chainage="min")
        ResultFrameAggregator("max", chainage="min", duplicate="first")
        ResultFrameAggregator(time="max")
        ResultFrameAggregator(time="max", chainage="first")

        with pytest.raises(ValueError):
            ResultFrameAggregator(["max"])

        with pytest.raises(ValueError):
            ResultFrameAggregator({"time": "max"})

    with pytest.raises(ValueError):
        ResultFrameAggregator(time="max", chainage=["first"])

    @pytest.mark.parametrize(
        "args,kwargs,expected",
        [
            (
                ["max"],
                {},
                {
                    "duplicate": "max",
                    "chainage": "max",
                    "time": "max",
                },
            ),
            (
                [],
                {"time": "max"},
                {
                    "duplicate": "max",
                    "chainage": "max",
                    "time": "max",
                },
            ),
            (
                [],
                {"time": "max", "chainage": "first"},
                {
                    "duplicate": "max",
                    "chainage": "first",
                    "time": "max",
                },
            ),
            (
                [],
                {"time": "max", "chainage": "first", "duplicate": "last"},
                {
                    "duplicate": "last",
                    "chainage": "first",
                    "time": "max",
                },
            ),
        ],
    )
    def test_init_agg_functions(self, args, kwargs, expected):
        rfa = ResultFrameAggregator(*args, **kwargs)
        assert rfa._agg_functions == expected

    def test_validate_levels(self):
        rfa = ResultFrameAggregator("max")
        rfa._validate_levels()

        with pytest.raises(ValueError):
            rfa._agg_levels = ("duplicate", "chainage", "times")
            rfa._validate_levels()
        with pytest.raises(ValueError):
            rfa._agg_levels = ("duplicate", "time", "chainage")
            rfa._validate_levels()
        with pytest.raises(ValueError):
            rfa._agg_levels = ("duplicate", "chainage", "chainage")
            rfa._validate_levels()

    def test_validate_agg_functions(self):
        rfa = ResultFrameAggregator("max")
        rfa._validate_agg_functions()

        with pytest.raises(ValueError):
            rfa._agg_functions = {"duplicate": ["max"], "chainage": "max"}
            rfa._validate_agg_functions()
        with pytest.raises(ValueError):
            rfa._agg_functions = {"duplicate": None, "time": "max"}
            rfa._validate_agg_functions()
        with pytest.raises(ValueError):
            rfa._agg_functions = {"time": ["min", "max"]}
            rfa._validate_agg_functions()
        with pytest.raises(ValueError):
            rfa._agg_functions = {"chainage": "max", "time": {}}
            rfa._validate_agg_functions()
        with pytest.raises(ValueError):
            rfa._agg_functions = {}
            rfa._validate_agg_functions()

    def test_validate_agg_function(self):
        rfa = ResultFrameAggregator("max", {"chainage": np.min})
        rfa._validate_agg_function("time", "max")

        with pytest.raises(ValueError):
            rfa._validate_agg_function("time", ["max"])

        with pytest.raises(ValueError):
            rfa._validate_agg_function("time", None)

    def test_entity_levels(self):
        rfa = ResultFrameAggregator("max")
        assert rfa.entity_levels == ("group", "name", "tag")

    def test_quantity_levels(self):
        rfa = ResultFrameAggregator("max")
        assert rfa.quantity_levels == ("quantity", "derived")

    def test_agg_levels(self):
        rfa = ResultFrameAggregator("max")
        assert rfa.agg_levels == ("duplicate", "chainage", "time")

    def test_agg_functions(self):
        rfa = ResultFrameAggregator("max")
        assert rfa.agg_functions == {
            "duplicate": "max",
            "chainage": "max",
            "time": "max",
        }
        rfa = ResultFrameAggregator(time="max", chainage="first", duplicate="last")
        assert rfa.agg_functions == {
            "duplicate": "last",
            "chainage": "first",
            "time": "max",
        }

    def test_set_agg_function(self):
        rfa = ResultFrameAggregator("max")
        rfa.set_agg_function("time", "mean")
        assert rfa.agg_functions["time"] == "mean"

        with pytest.raises(ValueError):
            rfa.set_agg_function("time", ["mean"])

        with pytest.raises(ValueError):
            rfa.set_agg_function("time", None)

    def test_get_agg_function(self):
        rfa = ResultFrameAggregator("max")
        assert rfa.get_agg_function("time") == "max"

        with pytest.raises(ValueError):
            rfa.get_agg_function("times")

        rfa.set_agg_function("chainage", "min")
        assert rfa.get_agg_function("chainage") == "min"

    @pytest.mark.parametrize(
        ["df", "expect_error"],
        [
            (pd.DataFrame(), True),
            (None, True),
            (create_dummy_dataframe(), False),
        ],
    )
    def test_validate_df(self, df, expect_error):
        rfa = ResultFrameAggregator("max")
        if expect_error:
            with pytest.raises(AttributeError):
                rfa._validate_df(df)
        else:
            rfa._validate_df(df)

    @pytest.mark.parametrize(
        ["level", "expect_error"],
        [
            (None, True),
            ("test", True),
            ("duplicate", False),
        ],
    )
    def test_has_level_name(self, df_dummy, level, expect_error):
        rfa = ResultFrameAggregator("max")
        if expect_error:
            assert not rfa._has_level_name(df_dummy, level)
        else:
            assert rfa._has_level_name(df_dummy, level)

    def test_aggregate_along_level(self, df_simple):
        rfa = ResultFrameAggregator("max")

        df_agg = rfa._aggregate_along_level(df_simple, "LA", "max")
        assert df_agg.shape == (2, 4)
        assert "LA" not in df_agg.columns.names
        assert list(df_agg.columns.values) == [
            ("B", "B"),
            ("B", "A"),
            ("A", "B"),
            ("A", "A"),
        ]
        remaining_levels = ["LB", "LC"]
        for L in remaining_levels:
            assert_array_equal(
                df_simple.columns.get_level_values(L), df_agg.columns.get_level_values(L)
            )
        assert_array_equal(df_simple.values, df_agg.values)

        df_agg = rfa._aggregate_along_level(df_simple, "LB", "max")
        assert df_agg.shape == (2, 2)
        assert "LB" not in df_agg.columns.names
        remaining_levels = ["LA", "LC"]
        assert list(df_agg.columns.values) == [
            ("A", "B"),
            ("A", "A"),
        ]
        assert_array_equal(df_agg.columns.get_level_values("LA"), ["A", "A"])
        assert_array_equal(df_agg.columns.get_level_values("LC"), ["B", "A"])
        assert_array_equal(df_agg.values, [[2, 3], [12, 13]])

        df_agg = rfa._aggregate_along_level(df_simple, "LC", "max")
        assert df_agg.shape == (2, 2)
        assert "LC" not in df_agg.columns.names
        remaining_levels = ["LA", "LB"]
        assert list(df_agg.columns.values) == [
            ("A", "B"),
            ("A", "A"),
        ]
        assert list(df_agg.columns.values) == [("A", "B"), ("A", "A")]
        assert_array_equal(df_agg.columns.get_level_values("LA"), ["A", "A"])
        assert_array_equal(df_agg.columns.get_level_values("LB"), ["B", "A"])
        assert_array_equal(df_agg.values, [[1, 3], [11, 13]])

        df_agg = rfa._aggregate_along_level(df_simple, "LC", "first")
        assert_array_equal(df_agg.values, [[0, 2], [10, 12]])

        df_agg = rfa._aggregate_along_level(df_simple, "LC", "last")
        assert_array_equal(df_agg.values, [[1, 3], [11, 13]])

        df_agg = rfa._aggregate_along_level(df_simple, "LC", "sum")
        assert_array_equal(df_agg.values, [[1, 5], [21, 25]])

    def test_aggregate_along_time(self, df_simple):
        rfa = ResultFrameAggregator("max")
        df_agg = rfa._aggregate_along_time(df_simple, "max")
        assert_index_equal(df_simple.columns, df_agg.columns)
        assert_array_equal(df_agg.values, [[10, 11, 12, 13]])

        df_agg = rfa._aggregate_along_time(df_simple, "min")
        assert_index_equal(df_simple.columns, df_agg.columns)
        assert_array_equal(df_agg.values, [[0, 1, 2, 3]])

    def test_finalize_df_post_aggregate(self, df_dummy):
        # Aggregator requires all groups be of same type
        df_dummy = df_dummy.T.query("group=='A'").T
        rfa = ResultFrameAggregator("max")
        df_agg = rfa.aggregate(df_dummy)
        expected_columns = set()
        for c in df_dummy.columns.get_level_values("quantity"):
            expected_columns.add(f"max_{c}")
        columns = set(df_agg.columns.values)
        assert expected_columns == columns


class TestResultFrameAggregator:
    @pytest.mark.parametrize("agg,expected", [("max", 102.7227), ("min", -0.1209)])
    @pytest.mark.parametrize("column_mode", ["all", "compact"])
    def test_aggregation_for_river_discharge(self, res1d_river_network, agg, expected, column_mode):
        df_reaches = res1d_river_network.reaches.river.Discharge.read(column_mode=column_mode)
        rfa = ResultFrameAggregator(agg)
        df_agg = rfa.aggregate(df_reaches)
        df_agg = df_agg.groupby("name").agg(agg)  # test max of entire reach (not segments)
        agg_value = df_agg.iloc[0, 0]
        assert agg_value == pytest.approx(expected, abs=1e-4)

    @pytest.mark.parametrize("column_mode", ["all", "compact"])
    def test_max_aggregation(self, res1d_river_network, column_mode):
        df_reaches = res1d_river_network.reaches.read(column_mode=column_mode)
        rfa = ResultFrameAggregator("max")
        df_agg = rfa.aggregate(df_reaches)
        df_agg = df_agg.groupby("name").agg("max")  # test for entire reach (not segments)

        assert list(df_agg.columns.values) == [
            "max_Discharge",
            "max_FlowVelocity",
            "max_ManningResistanceNumber",
            "max_WaterLevel",
        ]

        assert list(df_agg.index) == [
            "basin_left1",
            "basin_left2",
            "basin_right",
            "link_basin_left",
            "link_basin_left1_2",
            "link_basin_left2_2",
            "link_basin_right",
            "river",
            "tributary",
        ]

        # cheap expected value check
        df_agg_std = df_agg.std()
        assert list(df_agg_std.index) == [
            "max_Discharge",
            "max_FlowVelocity",
            "max_ManningResistanceNumber",
            "max_WaterLevel",
        ]
        assert list(df_agg_std.values) == pytest.approx(
            [32.83624888, 1.28741954, 3.25905542, 0.4820685]
        )

    @pytest.mark.parametrize("column_mode", ["all", "compact"])
    def test_lambda_aggregation_override_name(self, res1d_river_network, column_mode):
        df_reaches = res1d_river_network.reaches.read(column_mode=column_mode)
        rfa = ResultFrameAggregator(lambda x: x.abs().max(), override_name="max")
        df_agg = rfa.aggregate(df_reaches)

        assert list(df_agg.columns.values) == [
            "max_Discharge",
            "max_FlowVelocity",
            "max_ManningResistanceNumber",
            "max_WaterLevel",
        ]
