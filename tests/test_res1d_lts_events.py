import os
import pytest
import numpy as np
import pandas as pd

from mikeio1d.custom_exceptions import NoDataForQuery, InvalidQuantity
from mikeio1d.res1d import Res1D, mike1d_quantities, QueryDataReach, QueryDataNode
from mikeio1d.dotnet import to_numpy


@pytest.fixture
def test_file_path():
    test_folder_path = os.path.dirname(os.path.abspath(__file__))
    # Original file name was Exam6Base.res1d
    return os.path.join(test_folder_path, "testdata", "LTSEventStatistics.res1d")


@pytest.fixture(params=[False])
def test_file(test_file_path, request):
    return Res1D(test_file_path, request.param)


def test_file_does_not_exist():
    with pytest.raises(FileExistsError):
        assert Res1D("tests/testdata/not_a_file.res1d")


def test_read(test_file):
    df = test_file.read()
    assert len(df) == 10


def test_quantities(test_file):
    quantities = test_file.quantities
    assert len(quantities) == 24


@pytest.mark.parametrize("query,expected", [
    (QueryDataReach("WaterLevelMaximum", "B4.1320l1", 0), True),
    (QueryDataReach("WaterLevelMaximumTime", "B4.1320l1", 42424242), False),
    (QueryDataReach("WaterLevelMaximum", "wrong_reach_name", 0), False)
])
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


@pytest.mark.parametrize("query,expected_max", [
    (QueryDataReach("WaterLevelMaximum", "B4.1320l1", 135.001), 17.379),
    (QueryDataReach("WaterLevelMaximum", "B4.1491l1", 144), 18.638),
    (QueryDataReach("DischargeMaximum", "B4.1320l1", 270.002), 0.444),
    (QueryDataReach("DischargeMaximum", "B4.1491l1", 239.999), 0.151)
])
def test_read_reach_with_queries(test_file, query, expected_max):
    data = test_file.read(query)
    assert pytest.approx(round(data.max().values[0], 3)) == expected_max


@pytest.mark.parametrize("quantity,reach_id,chainage,expected_max", [
    ("WaterLevelMaximum", "B4.1320l1", 135.001, 17.379),
    ("WaterLevelMaximum", "B4.1491l1", 144, 18.638),
    ("DischargeMaximum", "B4.1320l1", 270.002, 0.444),
    ("DischargeMaximum", "B4.1491l1", 239.999, 0.151)
])
def test_read_reach(test_file, quantity, reach_id, chainage, expected_max):
    data = test_file.query.GetReachValues(reach_id, chainage, quantity)
    data = to_numpy(data)
    actual_max = round(np.max(data), 3)
    assert pytest.approx(actual_max) == expected_max


@pytest.mark.parametrize("quantity,node_id,expected_max", [
    ("WaterLevelMaximum", "B4.1320", 17.511),
    ("WaterLevelMaximum", "B4.1480", 16.957)
])
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


def test_res1d_filter(test_file_path):
    nodes = ["B4.1320", "A0.0327"]
    reaches = ["B4.1491l1"]
    res1d = Res1D(test_file_path, nodes=nodes, reaches=reaches)

    res1d.read(QueryDataReach("WaterLevelMaximum", "B4.1491l1", 144))
    res1d.read(QueryDataNode("WaterLevelMaximum", "B4.1320"))
    res1d.read(QueryDataNode("WaterLevelMaximum", "A0.0327"))

    # Release the .NET object
    res1d = None


def test_res1d_filter_readall(test_file_path):
    # Make sure read all can be used with filters
    nodes = ["B4.1320", "A0.0327"]
    reaches = ["B4.1491l1"]
    res1d = Res1D(test_file_path, nodes=nodes, reaches=reaches)

    res1d.read()

    # Release the .NET object
    res1d = None
