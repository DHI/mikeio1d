import os
import pytest
import numpy as np
import pandas as pd

import System

from mikeio1d.custom_exceptions import NoDataForQuery, InvalidQuantity
from mikeio1d.res1d import Res1D, mike1d_quantities, QueryDataReach, QueryDataNode
from mikeio1d.dotnet import to_numpy, from_dotnet_datetime, to_dotnet_datetime


@pytest.fixture
def test_file_path():
    test_folder_path = os.path.dirname(os.path.abspath(__file__))
    # Original file name was Exam6Base.res1d
    return os.path.join(test_folder_path, "testdata", "Network.res1d")


@pytest.fixture(params=[True, False])
def test_file(test_file_path, request):
    return Res1D(test_file_path, lazy_load=request.param)


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


def test_repr(test_file):
    res1d = test_file
    res1d_repr = res1d.__repr__()
    res1d_repr_ref = (
        "<mikeio1d.Res1D>\n"
        + "Start time: 1994-08-07 16:35:00\n"
        + "End time: 1994-08-07 18:35:00\n"
        "# Timesteps: 110\n"
        + "# Catchments: 0\n"
        + "# Nodes: 119\n"
        + "# Reaches: 118\n"
        + "# Globals: 0\n"
        "0 - WaterLevel <m>\n" + "1 - Discharge <m^3/s>"
    )
    assert res1d_repr == res1d_repr_ref


def test_data_item_dicts(test_file):
    res1d = test_file
    assert len(res1d.catchments) == 0
    assert len(res1d.nodes) == 119
    assert len(res1d.reaches) == 118
    assert len(res1d.structures) == 2
    assert len(res1d.global_data) == 0


@pytest.mark.parametrize(
    "query,expected",
    [
        (QueryDataReach("WaterLevel", "104l1", 34.4131), True),
        (QueryDataReach("WaterLevel", "104l1", 42424242), False),
        (QueryDataReach("WaterLevel", "wrong_reach_name", 34.4131), False),
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
        (QueryDataReach("WaterLevel", "104l1", 34.4131), 197.046),
        (QueryDataReach("WaterLevel", "9l1", 10), 195.165),
        (QueryDataReach("Discharge", "100l1", 23.8414), 0.1),
        (QueryDataReach("Discharge", "9l1", 5), 0.761),
    ],
)
def test_read_reach_with_queries(test_file, query, expected_max):
    data = test_file.read(query)
    assert pytest.approx(round(data.max().values[0], 3)) == expected_max


@pytest.mark.parametrize(
    "quantity,reach_id,chainage,expected_max",
    [
        ("WaterLevel", "104l1", 34.4131, 197.046),
        ("WaterLevel", "9l1", 10, 195.165),
        ("Discharge", "100l1", 23.8414, 0.1),
        ("Discharge", "9l1", 5, 0.761),
    ],
)
def test_read_reach(test_file, quantity, reach_id, chainage, expected_max):
    data = test_file.query.GetReachValues(reach_id, chainage, quantity)
    data = to_numpy(data)
    actual_max = round(np.max(data), 3)
    assert pytest.approx(actual_max) == expected_max


@pytest.mark.parametrize(
    "quantity,node_id,expected_max",
    [("WaterLevel", "1", 195.669), ("WaterLevel", "2", 195.823)],
)
def test_read_node(test_file, quantity, node_id, expected_max):
    data = test_file.query.GetNodeValues(node_id, quantity)
    data = to_numpy(data)
    actual_max = round(np.max(data), 3)
    assert pytest.approx(actual_max) == expected_max


def test_time_index(test_file):
    assert len(test_file.time_index) == 110


def test_start_time(test_file):
    assert test_file.start_time == test_file.time_index.min()


def test_from_dotnet_datetime_preserves_millisecond_precision():
    dtstr = "2021-01-01 00:00:00.123"

    dotnet_dt = System.DateTime.Parse(dtstr)
    assert dotnet_dt.Millisecond == 123
    py_dt = from_dotnet_datetime(dotnet_dt)
    # python datetime doesn't have a millisecond property so we use microsecond
    assert py_dt.microsecond == 123000


# Write the same test as above, but in the reverse direction
def test_to_dotnet_datetime_preserves_millisecond_precision():
    dtstr = "2021-01-01 00:00:00.123"

    py_dt = pd.to_datetime(dtstr)
    assert py_dt.microsecond == 123000
    dotnet_dt = to_dotnet_datetime(py_dt)
    assert dotnet_dt.Millisecond == 123


def test_time_index_microseconds(test_file):
    df = test_file.read()
    assert df.index.microsecond.unique().size > 1


def test_get_node_values(test_file):
    values = test_file.get_node_values("1", "WaterLevel")
    assert len(values) == 110


def test_get_reach_values(test_file):
    values = test_file.get_reach_values("9l1", 5, "WaterLevel")
    time_series = pd.Series(values, index=test_file.time_index)
    assert len(values) == 110
    assert len(time_series.index) == 110
    # Just try to call the methods
    test_file.get_reach_end_values("9l1", "WaterLevel")
    test_file.get_reach_start_values("9l1", "WaterLevel")
    test_file.get_reach_sum_values("9l1", "WaterLevel")


def test_get_reach_value(test_file):
    value = test_file.get_reach_value("9l1", 5, "WaterLevel", test_file.start_time)
    assert value > 0


def test_dotnet_methods(test_file):
    res1d = test_file
    # Just try to access the properties and methods in .net
    res1d.data.ResultSpecs
    res1d.data.Nodes
    res1d.query.GetNodeValues("1", "WaterLevel")
    res1d.query.GetReachValue(
        "9l1", 5, "WaterLevel", res1d.data.StartTime
    )  # must be dotnet datetime
    res1d.query.GetReachValues("9l1", 5, "WaterLevel")
    res1d.query.GetReachEndValues("9l1", "WaterLevel")  # avoid specifying chainage
    res1d.query.GetReachStartValues("9l1", "WaterLevel")  # avoid specifying chainage
    res1d.query.GetReachSumValues(
        "9l1", "WaterLevel"
    )  # useful for summing volume in reach (all grid points)


def test_res1d_filter(test_file_path):
    nodes = ["1", "2"]
    reaches = ["9l1"]
    res1d = Res1D(test_file_path, nodes=nodes, reaches=reaches)

    res1d.read(QueryDataReach("WaterLevel", "9l1", 10))
    res1d.read(QueryDataNode("WaterLevel", "1"))
    res1d.read(QueryDataNode("WaterLevel", "2"))

    # Currently Mike1D raises NullReferenceException when requesting location not included by filter
    # This should be fixed in Mike1D to raise more meaningful Mike1DException
    # with pytest.raises(Exception):
    #     assert res1d.read(QueryDataReach("WaterLevel", "100l1", 10))
    #     assert res1d.read(QueryDataNode("WaterLevel", "3"))


def test_res1d_filter_readall(test_file_path):
    # Make sure read all can be used with filters
    nodes = ["1", "2"]
    reaches = ["9l1"]
    res1d = Res1D(test_file_path, nodes=nodes, reaches=reaches)

    res1d.read()


def test_node_attributes(test_file):
    res1d = test_file
    nodes = res1d.nodes

    nodes.n_1.WaterLevel.add()
    nodes.n_2.WaterLevel.add()
    df = res1d.read()

    actual_max = round(df["WaterLevel:1"].max(), 3)
    assert pytest.approx(actual_max) == 195.669

    actual_max = round(df["WaterLevel:2"].max(), 3)
    assert pytest.approx(actual_max) == 195.823


def test_reach_attributes(test_file):
    res1d = test_file
    reaches = res1d.reaches

    reaches.r_104l1.m_34_4131.WaterLevel.add()

    reaches.r_9l1.m_10.WaterLevel.add()

    reaches.r_100l1.m_23_8414.Discharge.add()

    reaches.r_9l1.m_5.Discharge.add()

    df = res1d.read()

    actual_max = round(df["WaterLevel:104l1:34.4131"].max(), 3)
    assert pytest.approx(actual_max) == 197.046

    actual_max = round(df["WaterLevel:9l1:10"].max(), 3)
    assert pytest.approx(actual_max) == 195.165

    actual_max = round(df["Discharge:100l1:23.8414"].max(), 3)
    assert pytest.approx(actual_max) == 0.1

    actual_max = round(df["Discharge:9l1:5"].max(), 3)
    assert pytest.approx(actual_max) == 0.761


def test_structure_reach_attributes(test_file):
    res1d = test_file
    structures = res1d.structures

    structures.s_119w1.Discharge.add()
    structures.s_115p1.Discharge.add()

    df = res1d.read()

    max_discharge = round(df.max().max(), 3)
    assert pytest.approx(max_discharge) == 1.491
