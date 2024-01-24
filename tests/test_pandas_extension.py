import pytest
import pandas as pd
from pandas.testing import assert_frame_equal

from mikeio1d.pandas_extension import TransposedGroupBy
from mikeio1d.pandas_extension import groupby_chainage
from mikeio1d.pandas_extension import agg_chainage
from mikeio1d.pandas_extension import groupby_level

from mikeio1d.result_reader_writer.result_reader import ColumnMode


@pytest.fixture
def sample_dataframe(res1d_river_network) -> pd.DataFrame:
    df = res1d_river_network.read(column_mode=ColumnMode.COMPACT)
    return df


def test_groupby_chainage(sample_dataframe):
    # Test groupby_chainage function
    groupby = groupby_chainage(sample_dataframe)
    assert isinstance(groupby, TransposedGroupBy)
    assert groupby.max().max().max() == pytest.approx(sample_dataframe.max().max())
    assert groupby.min().min().min() == pytest.approx(sample_dataframe.min().min())


def test_groupby_level(sample_dataframe):
    groupby = groupby_level(sample_dataframe, level_name="chainage")
    assert isinstance(groupby, TransposedGroupBy)
    assert groupby.max().max().max() == pytest.approx(sample_dataframe.max().max())
    assert groupby.min().min().min() == pytest.approx(sample_dataframe.min().min())


def test_agg_chainage(sample_dataframe):
    # Test agg_chainage function
    agg_result = agg_chainage(sample_dataframe, agg=["max"])
    assert isinstance(agg_result, pd.DataFrame)
    assert agg_result.max().max() == pytest.approx(sample_dataframe.max().max())

    @pytest.fixture
    def sample_dataframe():
        # Create a sample transposed DataFrame
        df = pd.DataFrame({"quantity": ["A", "A", "B", "B"], "value": [1, 2, 3, 4]})
        return df


def test_transposed_groupby(sample_dataframe):
    groupby = sample_dataframe.T.groupby("quantity")
    groupby_transposed = TransposedGroupBy(groupby)
    assert groupby_transposed.transposed_groupby is groupby

    df_expected = groupby.max().T
    df = groupby_transposed.max()

    assert_frame_equal(df, df_expected)

    df_expected = groupby.min().T
    df = groupby_transposed.min()
    assert_frame_equal(df, df_expected)

    df_expected = groupby.first().T
    df = groupby_transposed.first()
    assert_frame_equal(df, df_expected)


def test_m1d_accessor(sample_dataframe):
    assert sample_dataframe.m1d is not None


def test_m1d_agg_chainage(sample_dataframe):
    df_expected = agg_chainage(sample_dataframe)
    df = sample_dataframe.m1d.agg_chainage()
    assert_frame_equal(df, df_expected)

    df_expected = agg_chainage(sample_dataframe, agg=["max"])
    df = sample_dataframe.m1d.agg_chainage(agg=["max"])
    assert_frame_equal(df, df_expected)


def test_m1d_groupby_chainage(sample_dataframe):
    df_expected = groupby_chainage(sample_dataframe).nth(0)
    df = sample_dataframe.m1d.groupby_chainage().nth(0)
    assert_frame_equal(df, df_expected)


def test_m1d_query(sample_dataframe):
    df_expected = sample_dataframe.T.query("quantity == 'WaterLevel'").T
    df = sample_dataframe.m1d.query("quantity == 'WaterLevel'")
    assert_frame_equal(df, df_expected)


def test_m1d_groupby(sample_dataframe):
    df_expected = sample_dataframe.T.groupby("quantity").max().T
    df = sample_dataframe.m1d.groupby("quantity").max()
    assert_frame_equal(df, df_expected)


def test_m1d_groupby_level(sample_dataframe):
    df_expected = groupby_level(sample_dataframe, level_name="quantity").max()
    df = sample_dataframe.m1d.groupby_level("quantity").max()
    assert_frame_equal(df, df_expected)
