import os
import pytest
import numpy as np
import pandas as pd

from mikeio1d.custom_exceptions import NoDataForQuery, InvalidQuantity
from mikeio1d.res1d import Res1D
from mikeio1d.query import QueryDataReach
from mikeio1d.query import QueryDataNode
from mikeio1d.dotnet import to_numpy
from mikeio1d.result_reader_writer.result_reader import ColumnMode


@pytest.fixture
def test_file_path():
    test_folder_path = os.path.dirname(os.path.abspath(__file__))
    # Original file name was Exam6Base.res1d
    return os.path.join(test_folder_path, "testdata", "lts_event_statistics.res1d")


@pytest.fixture(params=[False])
def test_file(test_file_path, request):
    return Res1D(test_file_path, lazy_load=request.param)


def test_file_does_not_exist():
    with pytest.raises(FileExistsError):
        assert Res1D("tests/testdata/not_a_file.res1d")


def test_read(test_file):
    df = test_file.read()
    assert len(df) == 10
    # TODO: assert not df.columns.duplicated().any() - add this, but it fails since columns are not guaranteed unique


def test_quantities(test_file):
    quantities = test_file.quantities
    assert len(quantities) == 24


def test_info(test_file):
    res1d = test_file
    res1d_info = res1d._get_info()
    res1d_info_ref = (
        "Start time: 1957-01-01 00:00:00\n"
        + "End time: 1963-01-01 00:00:00\n"
        + "# Timesteps: 10\n"
        + "# Catchments: 0\n"
        + "# Nodes: 16\n"
        + "# Reaches: 17\n"
        + "# Globals: 0\n"
        + "0 - WaterLevelMaximum <m>\n"
        + "1 - WaterLevelMaximumTime <sec>\n"
        + "2 - DischargeIntegrated <m^3>\n"
        + "3 - DischargeIntegratedTime <sec>\n"
        + "4 - DischargeMaximum <m^3/s>\n"
        + "5 - DischargeMaximumTime <sec>\n"
        + "6 - DischargeDuration <h>\n"
        + "7 - DischargeDurationTime <sec>\n"
        + "8 - Component_1Maximum <kg/m^3>\n"
        + "9 - Component_1MaximumTime <sec>\n"
        + "10 - Component_2Maximum <kg/m^3>\n"
        + "11 - Component_2MaximumTime <sec>\n"
        + "12 - Component_1TransportIntegrated <kg>\n"
        + "13 - Component_1TransportIntegratedTime <sec>\n"
        + "14 - Component_2TransportIntegrated <kg>\n"
        + "15 - Component_2TransportIntegratedTime <sec>\n"
        + "16 - SurchargeMaximum <m^3/s>\n"
        + "17 - SurchargeMaximumTime <sec>\n"
        + "18 - SurchargeIntegrated <m^3>\n"
        + "19 - SurchargeIntegratedTime <sec>\n"
        + "20 - SurchargeDuration <h>\n"
        + "21 - SurchargeDurationTime <sec>\n"
        + "22 - FlowVelocityMaximum <m/s>\n"
        + "23 - FlowVelocityMaximumTime <sec>"
    )
    assert res1d_info == res1d_info_ref


def test_data_item_dicts(test_file):
    res1d = test_file
    assert len(res1d.catchments) == 0
    assert len(res1d.nodes) == 16
    assert len(res1d.reaches) == 17
    assert len(res1d.global_data) == 0


@pytest.mark.parametrize(
    "query,expected",
    [
        (QueryDataReach("WaterLevelMaximum", "B4.1320l1", 0), True),
        (QueryDataReach("WaterLevelMaximumTime", "B4.1320l1", 42424242), False),
        (QueryDataReach("WaterLevelMaximum", "wrong_reach_name", 0), False),
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
        (QueryDataReach("WaterLevelMaximum", "B4.1320l1", 135.001), 17.379),
        (QueryDataReach("WaterLevelMaximum", "B4.1491l1", 144), 18.638),
        (QueryDataReach("DischargeMaximum", "B4.1320l1", 270.002), 0.444),
        (QueryDataReach("DischargeMaximum", "B4.1491l1", 239.999), 0.151),
    ],
)
def test_read_reach_with_queries(test_file, query, expected_max):
    data = test_file.read(query)
    assert pytest.approx(round(data.max().values[0], 3)) == expected_max


@pytest.mark.parametrize(
    "quantity,reach_id,chainage,expected_max",
    [
        ("WaterLevelMaximum", "B4.1320l1", 135.001, 17.379),
        ("WaterLevelMaximum", "B4.1491l1", 144, 18.638),
        ("DischargeMaximum", "B4.1320l1", 270.002, 0.444),
        ("DischargeMaximum", "B4.1491l1", 239.999, 0.151),
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
        ("WaterLevelMaximum", "B4.1320", 17.511),
        ("WaterLevelMaximum", "B4.1480", 16.957),
    ],
)
def test_read_node(test_file, quantity, node_id, expected_max):
    data = test_file.query.GetNodeValues(node_id, quantity)
    data = to_numpy(data)
    actual_max = round(np.max(data), 3)
    assert pytest.approx(actual_max) == expected_max


def test_time_index(test_file):
    assert len(test_file.time_index) == 10


def test_lts_event_index(test_file):
    for i in range(len(test_file.time_index)):
        assert test_file.time_index[i] == i


def test_get_node_values(test_file):
    values = test_file.get_node_values("B4.1320", "WaterLevelMaximumTime")
    assert len(values) == 10


def test_get_reach_values(test_file):
    values = test_file.get_reach_values("B4.1491l1", 144, "WaterLevelMaximumTime")
    time_series = pd.Series(values, index=test_file.time_index)
    assert len(values) == 10
    assert len(time_series.index) == 10
    # Just try to call the methods
    test_file.get_reach_end_values("B4.1491l1", "WaterLevelMaximumTime")
    test_file.get_reach_start_values("B4.1491l1", "WaterLevelMaximumTime")
    test_file.get_reach_sum_values("B4.1491l1", "WaterLevelMaximumTime")


def test_get_reach_value(test_file):
    with pytest.raises(NotImplementedError):
        assert test_file.get_reach_value("B4.1491l1", 144, "WaterLevel", 1)


def test_res1d_filter(test_file_path, helpers):
    nodes = ["B4.1320", "A0.0327"]
    reaches = ["B4.1491l1"]
    res1d = Res1D(test_file_path, nodes=nodes, reaches=reaches)
    res1d.result_reader.column_mode = ColumnMode.ALL

    df_b4_14 = res1d.read(QueryDataReach("WaterLevelMaximum", "B4.1491l1", 144))
    df_b4_13 = res1d.read(QueryDataNode("WaterLevelMaximum", "B4.1320"))
    df_a0 = res1d.read(QueryDataNode("WaterLevelMaximum", "A0.0327"))

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


def test_res1d_merging_same_file(test_file_path):
    # Use the same file twice to create a merged LTS statistics file
    file_names = [test_file_path, test_file_path]
    merged_file_name = test_file_path.replace(".res1d", ".merged.res1d")
    Res1D.merge(file_names, merged_file_name)

    # Read the merged file
    res1d = Res1D(merged_file_name)

    # Test one node location for particular values
    df_node = res1d.nodes.B4_1320.WaterLevelMaximum.read()
    b4_1320_event1 = df_node.iloc[0].iloc[0]
    b4_1320_event2 = df_node.iloc[1].iloc[0]
    assert b4_1320_event1 == b4_1320_event2
    assert pytest.approx(np.round(b4_1320_event1, 3)) == 17.511

    df_node_time = res1d.nodes.B4_1320.WaterLevelMaximumTime.read()
    b4_1320_time1 = df_node_time.iloc[0]
    b4_1320_time2 = df_node_time.iloc[1]
    assert (b4_1320_time1 == b4_1320_time2).values[0]

    # Test one reach location for particular values
    df_reach = res1d.reaches.B4_1491l1.m_216.DischargeMaximum.read()
    b4_1491l1_event1 = df_reach.iloc[0].iloc[0]
    b4_1491l1_event2 = df_reach.iloc[1].iloc[0]
    assert b4_1491l1_event1 == b4_1491l1_event2
    assert pytest.approx(np.round(b4_1491l1_event1, 3)) == 0.151

    df_reach_time = res1d.reaches.B4_1491l1.m_216.DischargeMaximumTime.read()
    b4_1491l1_time1 = df_reach_time.iloc[0]
    b4_1491l1_time2 = df_reach_time.iloc[1]
    assert (b4_1491l1_time1 == b4_1491l1_time2).values[0]

    # Validate all merged events. Every event now needs to appear twice.
    df = res1d.read_all()
    # TODO: Maybe it is possible to vectorize this check.
    for col in df:
        for i in range(0, len(df[col]), 2):
            assert df[col][i] == df[col][i + 1]
