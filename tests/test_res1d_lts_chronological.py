import os
import pytest
import numpy as np
import pandas as pd
import datetime

from mikeio1d.custom_exceptions import NoDataForQuery, InvalidQuantity
from mikeio1d.res1d import Res1D, mike1d_quantities, QueryDataReach, QueryDataNode
from mikeio1d.dotnet import to_numpy


@pytest.fixture
def test_file_path():
    test_folder_path = os.path.dirname(os.path.abspath(__file__))
    # Original file name was Exam6Base.res1d
    return os.path.join(test_folder_path, "testdata", "LTSMonthlyStatistics.res1d")


@pytest.fixture(params=[False])
def test_file(test_file_path, request):
    return Res1D(test_file_path, lazy_load=request.param)


def test_file_does_not_exist():
    with pytest.raises(FileExistsError):
        assert Res1D("tests/testdata/not_a_file.res1d")


def test_read(test_file):
    df = test_file.read()
    assert len(df) == 73


def test_quantities(test_file):
    quantities = test_file.quantities
    assert len(quantities) == 21


@pytest.mark.parametrize("query,expected", [
    (QueryDataReach("DischargeIntegratedMonthly", "B4.1320l1", 0), True),
    (QueryDataReach("DischargeIntegratedMonthly", "B4.1320l1", 42424242), False),
    (QueryDataReach("DischargeIntegratedMonthly", "wrong_reach_name", 0), False)
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
    (QueryDataReach("DischargeIntegratedMonthly", "B4.1320l1", 135.001), 1215.915),
    (QueryDataReach("DischargeIntegratedMonthly", "B4.1491l1", 144), 563.973),
    (QueryDataReach("DischargeIntegratedMonthlyCount", "B4.1320l1", 270.002), 3),
    (QueryDataReach("DischargeIntegratedMonthlyCount", "B4.1491l1", 239.999), 3)
])
def test_read_reach_with_queries(test_file, query, expected_max):
    data = test_file.read(query)
    assert pytest.approx(round(data.max().values[0], 3)) == expected_max


@pytest.mark.parametrize("quantity,reach_id,chainage,expected_max", [
    ("DischargeIntegratedMonthly", "B4.1320l1", 135.001, 1215.915),
    ("DischargeIntegratedMonthly", "B4.1491l1", 144, 563.973),
    ("DischargeIntegratedMonthlyCount", "B4.1320l1", 270.002, 3),
    ("DischargeIntegratedMonthlyCount", "B4.1491l1", 239.999, 3)
])
def test_read_reach(test_file, quantity, reach_id, chainage, expected_max):
    data = test_file.query.GetReachValues(reach_id, chainage, quantity)
    data = to_numpy(data)
    actual_max = round(np.max(data), 3)
    assert pytest.approx(actual_max) == expected_max


@pytest.mark.parametrize("quantity,node_id,expected_max", [
    ("SurchargeIntegratedMonthly", "B4.1200", 97.434),
    ("SurchargeIntegratedMonthlyCount", "B4.1200", 1)
])
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
    value = test_file.get_reach_value("B4.1491l1", 144, "DischargeIntegratedMonthlyCount", test_file.start_time)
    assert value == 0


def test_res1d_filter(test_file_path):
    nodes = ["B4.1320", "A0.0327"]
    reaches = ["B4.1491l1"]
    res1d = Res1D(test_file_path, nodes=nodes, reaches=reaches)

    res1d.read(QueryDataReach("DischargeIntegratedMonthly", "B4.1491l1", 144))
    res1d.read(QueryDataNode("SurchargeIntegratedMonthly", "B4.1320"))
    res1d.read(QueryDataNode("DischargeIntegratedMonthly", "A0.0327"))

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
