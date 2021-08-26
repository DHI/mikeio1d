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
    return os.path.join(test_folder_path, "testdata", "Network.res1d")


@pytest.fixture(params=[True, False])
def test_file(test_file_path, request):
    return Res1D(test_file_path, request.param)


def test_file_does_not_exist():
    with pytest.raises(FileExistsError):
        assert Res1D("tests/testdata/not_a_file.res1d")


def test_read(test_file):
    df = test_file.read()
    assert len(df) == 110


def test_mike1d_quantities():
    quantities = mike1d_quantities()
    assert "WaterLevel" in quantities


def test_quantities(test_file):
    quantities = test_file.quantities
    assert len(quantities) == 2


@pytest.mark.parametrize("query,expected", [
    (QueryDataReach("WaterLevel", "104l1", 34.4131), True),
    (QueryDataReach("WaterLevel", "104l1", 42424242), False),
    (QueryDataReach("WaterLevel", "wrong_reach_name", 34.4131), False)
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
    (QueryDataReach("WaterLevel", "104l1", 34.4131), 197.046),
    (QueryDataReach("WaterLevel", "9l1", 10), 195.165),
    (QueryDataReach("Discharge", "100l1", 23.8414), 0.1),
    (QueryDataReach("Discharge", "9l1", 5), 0.761)
])
def test_read_reach_with_queries(test_file, query, expected_max):
    data = test_file.read(query)
    assert pytest.approx(round(data.max().values[0], 3)) == expected_max


@pytest.mark.parametrize("quantity,reach_id,chainage,expected_max", [
    ("WaterLevel", "104l1", 34.4131, 197.046),
    ("WaterLevel", "9l1", 10, 195.165),
    ("Discharge", "100l1", 23.8414, 0.1),
    ("Discharge", "9l1", 5, 0.761)
])
def test_read_reach(test_file, quantity, reach_id, chainage, expected_max):
    data = test_file.query.GetReachValues(reach_id, chainage, quantity)
    data = to_numpy(data)
    actual_max = round(np.max(data), 3)
    assert pytest.approx(actual_max) == expected_max


@pytest.mark.parametrize("quantity,node_id,expected_max", [
    ("WaterLevel", "1", 195.669),
    ("WaterLevel", "2", 195.823)
])
def test_read_node(test_file, quantity, node_id, expected_max):
    data = test_file.query.GetNodeValues(node_id, quantity)
    data = to_numpy(data)
    actual_max = round(np.max(data), 3)
    assert pytest.approx(actual_max) == expected_max


def test_time_index(test_file):
    assert len(test_file.time_index) == 110


def test_start_time(test_file):
    assert test_file.start_time == test_file.time_index.min()


def test_get_node_values(test_file):
    values = test_file.get_node_values("1", "WaterLevel")
    assert len(values) == 110


def test_get_reach_values(test_file):
    values = test_file.get_reach_values("9l1", 5, "WaterLevel")
    time_series = pd.Series(values, index=test_file.time_index)
    assert len(values) == 110
    assert len(time_series.index) == 110
    values_end = test_file.get_reach_end_values("9l1", "WaterLevel")
    values_start = test_file.get_reach_start_values("9l1", "WaterLevel")
    values_sum = test_file.get_reach_sum_values("9l1", "WaterLevel")


def test_get_reach_value(test_file):
    value = test_file.get_reach_value("9l1", 5, "WaterLevel", test_file.start_time)
    assert value > 0


def test_dotnet_methods(test_file):
    res1d = test_file
    result_specs = res1d.data.ResultSpecs
    nodes = res1d.data.Nodes
    values = res1d.query.GetNodeValues("1", "WaterLevel")
    values = res1d.query.GetReachValue("9l1", 5, "WaterLevel", res1d.data.StartTime)  # must be dotnet datetime
    values = res1d.query.GetReachValues("9l1", 5, "WaterLevel")
    values = res1d.query.GetReachEndValues("9l1", "WaterLevel")  # avoid specifying chainage
    values = res1d.query.GetReachStartValues("9l1", "WaterLevel")  # avoid specifying chainage
    values = res1d.query.GetReachSumValues("9l1", "WaterLevel")  # useful for summing volume in reach (all grid points)


def test_res1d_filter(test_file_path):
    nodes = ["1", "2"]
    reaches = ["9l1"]
    res1d = Res1D(test_file_path, nodes=nodes, reaches=reaches)

    res1d.read(QueryDataReach("WaterLevel", "9l1", 10))
    res1d.read(QueryDataNode("WaterLevel", "1"))
    res1d.read(QueryDataNode("WaterLevel", "2"))

    # Currently Mike1D raises NullReferenceException when requesting location not included by filter
    # This should be fixed in Mike1D to raise more meaningful Mike1DException
    #with pytest.raises(Exception):
    #    assert res1d.read(QueryDataReach("WaterLevel", "100l1", 10))
    #    assert res1d.read(QueryDataNode("WaterLevel", "3"))
