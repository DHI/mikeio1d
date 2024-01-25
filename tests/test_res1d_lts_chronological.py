import os
import pytest
import numpy as np
import pandas as pd
import datetime

from mikeio1d.custom_exceptions import NoDataForQuery, InvalidQuantity
from mikeio1d.res1d import Res1D
from mikeio1d.query import QueryDataReach
from mikeio1d.query import QueryDataNode
from mikeio1d.query import QueryDataGlobal
from mikeio1d.dotnet import to_numpy
from mikeio1d.result_reader_writer.result_reader import ColumnMode


@pytest.fixture
def test_file_path():
    test_folder_path = os.path.dirname(os.path.abspath(__file__))
    # Original file name was Exam6Base.res1d
    return os.path.join(test_folder_path, "testdata", "lts_monthly_statistics.res1d")


@pytest.fixture(params=[False])
def test_file(test_file_path, request):
    return Res1D(test_file_path, lazy_load=request.param)


def test_file_does_not_exist():
    with pytest.raises(FileExistsError):
        assert Res1D("tests/testdata/not_a_file.res1d")


def test_read(test_file):
    df = test_file.read()
    assert len(df) == 73
    # TODO: assert not df.columns.duplicated().any() - add this, but it fails since columns are not guaranteed unique


def test_quantities(test_file):
    quantities = test_file.quantities
    assert len(quantities) == 21


def test_info(test_file):
    res1d = test_file
    res1d_info = res1d._get_info()
    res1d_info_ref = (
        "Start time: 1957-01-01 00:00:00\n"
        + "End time: 1963-01-01 00:00:00\n"
        + "# Timesteps: 73\n"
        + "# Catchments: 0\n"
        + "# Nodes: 16\n"
        + "# Reaches: 17\n"
        + "# Globals: 9\n"
        + "0 - DischargeIntegratedMonthly <m^3>\n"
        + "1 - DischargeIntegratedMonthlyCount <()>\n"
        + "2 - DischargeIntegratedMonthlyDuration <h>\n"
        + "3 - Component_1TransportIntegratedMonthly <kg>\n"
        + "4 - Component_1TransportIntegratedMonthlyCount <()>\n"
        + "5 - Component_1TransportIntegratedMonthlyDuration <h>\n"
        + "6 - Component_2TransportIntegratedMonthly <kg>\n"
        + "7 - Component_2TransportIntegratedMonthlyCount <()>\n"
        + "8 - Component_2TransportIntegratedMonthlyDuration <h>\n"
        + "9 - SurchargeIntegratedMonthly <m^3>\n"
        + "10 - SurchargeIntegratedMonthlyCount <()>\n"
        + "11 - SurchargeIntegratedMonthlyDuration <h>\n"
        + "12 - DischargeIntegratedMonthlyOutlets <m^3>\n"
        + "13 - DischargeIntegratedMonthlyWeirs <m^3>\n"
        + "14 - DischargeIntegratedMonthlyTotalOutflow <m^3>\n"
        + "15 - Component_1TransportIntegratedMonthlyTotalEmission <kg>\n"
        + "16 - Component_2TransportIntegratedMonthlyTotalEmission <kg>\n"
        + "17 - Component_1TransportIntegratedMonthlyOutlets <kg>\n"
        + "18 - Component_2TransportIntegratedMonthlyOutlets <kg>\n"
        + "19 - Component_1TransportIntegratedMonthlyWeirs <kg>\n"
        + "20 - Component_2TransportIntegratedMonthlyWeirs <kg>"
    )
    assert res1d_info == res1d_info_ref


def test_data_item_dicts(test_file):
    res1d = test_file
    assert len(res1d.catchments) == 0
    assert len(res1d.nodes) == 16
    assert len(res1d.reaches) == 17
    assert len(res1d.global_data) == 9


@pytest.mark.parametrize(
    "query,expected",
    [
        (QueryDataReach("DischargeIntegratedMonthly", "B4.1320l1", 0), True),
        (QueryDataReach("DischargeIntegratedMonthly", "B4.1320l1", 42424242), False),
        (QueryDataReach("DischargeIntegratedMonthly", "wrong_reach_name", 0), False),
    ],
)
def test_valid_reach_data_queries(test_file, query, expected):
    res1d = test_file

    with pytest.raises(InvalidQuantity):
        invalid_query = QueryDataReach("InvalidQuantity", "104l1", 34.4131)
        assert res1d.read(invalid_query)

    if expected:
        res1d.read(query)
    else:
        with pytest.raises(NoDataForQuery):
            assert res1d.read(query)


@pytest.mark.parametrize(
    "query,expected_max",
    [
        (QueryDataReach("DischargeIntegratedMonthly", "B4.1320l1", 135.001), 1215.915),
        (QueryDataReach("DischargeIntegratedMonthly", "B4.1491l1", 144), 563.973),
        (QueryDataReach("DischargeIntegratedMonthlyCount", "B4.1320l1", 270.002), 3),
        (QueryDataReach("DischargeIntegratedMonthlyCount", "B4.1491l1", 239.999), 3),
    ],
)
def test_read_reach_with_queries(test_file, query, expected_max):
    data = test_file.read(query)
    assert pytest.approx(round(data.max().values[0], 3)) == expected_max


@pytest.mark.parametrize(
    "quantity,reach_id,chainage,expected_max",
    [
        ("DischargeIntegratedMonthly", "B4.1320l1", 135.001, 1215.915),
        ("DischargeIntegratedMonthly", "B4.1491l1", 144, 563.973),
        ("DischargeIntegratedMonthlyCount", "B4.1320l1", 270.002, 3),
        ("DischargeIntegratedMonthlyCount", "B4.1491l1", 239.999, 3),
    ],
)
def test_read_reach(test_file, quantity, reach_id, chainage, expected_max):
    data = test_file.query.GetReachValues(reach_id, chainage, quantity)
    data = to_numpy(data)
    actual_max = round(np.max(data), 3)
    assert pytest.approx(actual_max) == expected_max


@pytest.mark.parametrize(
    "quantity,node_id,expected_max",
    [
        ("SurchargeIntegratedMonthly", "B4.1200", 97.434),
        ("SurchargeIntegratedMonthlyCount", "B4.1200", 1),
    ],
)
def test_read_node(test_file, quantity, node_id, expected_max):
    data = test_file.query.GetNodeValues(node_id, quantity)
    data = to_numpy(data)
    actual_max = round(np.max(data), 3)
    assert pytest.approx(actual_max) == expected_max


def test_time_index(test_file):
    assert len(test_file.time_index) == 73


def test_start_time(test_file):
    time = test_file.start_time
    date = datetime.datetime(time.year, time.month, 1, 0, 0)
    assert date == test_file.time_index.min()


def test_get_node_values(test_file):
    values = test_file.get_node_values("B4.1200", "SurchargeIntegratedMonthly")
    assert len(values) == 73


def test_get_reach_values(test_file):
    values = test_file.get_reach_values("B4.1491l1", 144, "DischargeIntegratedMonthlyCount")
    time_series = pd.Series(values, index=test_file.time_index)
    assert len(values) == 73
    assert len(time_series.index) == 73
    # Just try to call the methods
    test_file.get_reach_end_values("B4.1491l1", "DischargeIntegratedMonthlyCount")
    test_file.get_reach_start_values("B4.1491l1", "DischargeIntegratedMonthlyCount")
    test_file.get_reach_sum_values("B4.1491l1", "DischargeIntegratedMonthlyCount")


def test_get_reach_value(test_file):
    value = test_file.get_reach_value(
        "B4.1491l1", 144, "DischargeIntegratedMonthlyCount", test_file.start_time
    )
    assert value == 0


def test_res1d_filter(test_file_path, helpers):
    nodes = ["B4.1320", "A0.0327"]
    reaches = ["B4.1491l1"]
    res1d = Res1D(test_file_path, nodes=nodes, reaches=reaches)
    res1d.result_reader.column_mode = ColumnMode.ALL

    df_b4_14 = res1d.read(QueryDataReach("DischargeIntegratedMonthly", "B4.1491l1", 144))
    df_b4_13 = res1d.read(QueryDataNode("SurchargeIntegratedMonthly", "B4.1320"))
    df_a0 = res1d.read(QueryDataNode("DischargeIntegratedMonthly", "A0.0327"))

    res1d_full = Res1D(test_file_path)
    res1d_full.result_reader.column_mode = ColumnMode.ALL
    df_full = res1d_full.read()

    helpers.assert_shared_columns_equal(df_full, df_b4_14)
    helpers.assert_shared_columns_equal(df_full, df_b4_13)
    helpers.assert_shared_columns_equal(df_full, df_a0)

    # Release the .NET object
    res1d = None


def test_res1d_filter_readall(test_file_path, helpers):
    # Make sure read all can be used with filters
    nodes = ["B4.1320", "A0.0327"]
    reaches = ["B4.1491l1"]
    res1d = Res1D(test_file_path, nodes=nodes, reaches=reaches)
    df = res1d.read()

    res1d_full = Res1D(test_file_path)
    df_full = res1d_full.read()

    helpers.assert_shared_columns_equal(df_full, df)

    # Release the .NET object
    res1d = None


@pytest.mark.parametrize(
    "query,expected_max",
    [
        (QueryDataGlobal("DischargeIntegratedMonthlyOutlets"), 5562.719),
        (QueryDataGlobal("DischargeIntegratedMonthlyWeirs"), 437.729),
        (QueryDataGlobal("DischargeIntegratedMonthlyTotalOutflow"), 5971.352),
    ],
)
def test_read_global_items_with_queries(test_file, query, expected_max):
    data = test_file.read(query)
    assert pytest.approx(round(data.max().values[0], 3)) == expected_max


def test_global_data_attributes(test_file):
    res1d = test_file
    global_data = res1d.global_data

    global_data.DischargeIntegratedMonthlyOutlets.add()
    global_data.DischargeIntegratedMonthlyWeirs.add()
    global_data.DischargeIntegratedMonthlyTotalOutflow.add()

    df = res1d.read()

    actual_max = round(df["DischargeIntegratedMonthlyOutlets"].max(), 3)
    assert pytest.approx(actual_max) == 5562.719

    actual_max = round(df["DischargeIntegratedMonthlyWeirs"].max(), 3)
    assert pytest.approx(actual_max) == 437.729

    actual_max = round(df["DischargeIntegratedMonthlyTotalOutflow"].max(), 3)
    assert pytest.approx(actual_max) == 5971.352


def test_res1d_merging_same_file(test_file_path):
    # Use the same file twice to create a merged LTS statistics file
    file_names = [test_file_path, test_file_path]
    merged_file_name = test_file_path.replace(".res1d", ".merged.res1d")
    Res1D.merge(file_names, merged_file_name)

    # Read the merged file
    res1d = Res1D(merged_file_name)

    # Test one reach location for particular values
    df_reach = res1d.reaches.B4_1320l1.m_101_251.DischargeIntegratedMonthly.read()
    assert pytest.approx(np.round(df_reach.max(), 3)) == 2 * 1215.915

    df_reach_count = res1d.reaches.B4_1320l1.m_101_251.DischargeIntegratedMonthlyCount.read()
    assert pytest.approx(np.round(df_reach_count.max(), 3)) == 2 * 3

    df_reach_duration = res1d.reaches.B4_1320l1.m_101_251.DischargeIntegratedMonthlyDuration.read()
    assert pytest.approx(np.round(df_reach_duration.max(), 3)) == 2 * 10.703

    res1d_ori = Res1D(test_file_path)
    df_ori = res1d_ori.read()
    df_merged = res1d.read()
    pd.testing.assert_frame_equal(2 * df_ori, df_merged)
