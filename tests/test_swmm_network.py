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
    # Original file name was Exam6Base.epanet_res
    return os.path.join(test_folder_path, "testdata", "Swmm.out")


@pytest.fixture(params=[False])
def test_file(test_file_path, request):
    return Res1D(test_file_path, lazy_load=request.param)


def test_read(test_file):
    df = test_file.read()
    assert len(df) == 36


def test_quantities(test_file):
    quantities = test_file.quantities
    assert len(quantities) == 36


@pytest.mark.parametrize("query,expected", [
    (QueryDataReach("SWMM_LINK_FLOW", "10"), True),
    (QueryDataReach("SWMM_LINK_FLOW", "10xyz"), False),
    (QueryDataReach("SWMM_LINK_FLOW", "wrong_reach_name"), False)
])
def test_valid_reach_data_queries(test_file, query, expected):
    epanet_res = test_file

    with pytest.raises(InvalidQuantity):
        invalid_query = QueryDataReach("InvalidQuantity", "10")
        assert epanet_res.read(invalid_query)

    if expected:
        epanet_res.read(query)
    else:
        with pytest.raises(Exception):
            assert epanet_res.read(query)


@pytest.mark.parametrize("query,expected_max", [
    (QueryDataReach("SWMM_LINK_FLOW", "10"), 18.204),
    (QueryDataReach("SWMM_LINK_FLOW", "12"), 2.43),
    (QueryDataReach("SWMM_LINK_DEPTH", "10"), 1.063),
    (QueryDataReach("SWMM_LINK_DEPTH", "12"), 0.462)
])
def test_read_reach_with_queries(test_file, query, expected_max):
    data = test_file.read(query)
    assert pytest.approx(round(data.max().values[0], 3)) == expected_max


@pytest.mark.parametrize("quantity,reach_id,expected_max", [
    ("SWMM_LINK_FLOW", "10", 18.204),
    ("SWMM_LINK_FLOW", "12", 2.43),
    ("SWMM_LINK_DEPTH", "10", 1.063),
    ("SWMM_LINK_DEPTH", "12", 0.462)
])
def test_read_reach(test_file, quantity, reach_id, expected_max):
    data = test_file.query.GetReachStartValues(reach_id, quantity)
    data = to_numpy(data)
    actual_max = round(np.max(data), 3)
    assert pytest.approx(actual_max) == expected_max


@pytest.mark.parametrize("quantity,node_id,expected_max", [
    ("SWMM_NODE_DEPTH", "9", 0.568),
    ("SWMM_NODE_DEPTH", "10", 3.0)
])
def test_read_node(test_file, quantity, node_id, expected_max):
    data = test_file.query.GetNodeValues(node_id, quantity)
    data = to_numpy(data)
    actual_max = round(np.max(data), 3)
    assert pytest.approx(actual_max) == expected_max


def test_time_index(test_file):
    assert len(test_file.time_index) == 36


def test_start_time(test_file):
    assert test_file.start_time == test_file.time_index.min()


def test_get_node_values(test_file):
    values = test_file.get_node_values("10", "SWMM_NODE_DEPTH")
    assert len(values) == 36


def test_get_reach_values(test_file):
    # When reading EPANET results there is a bug in MIKE 1D,
    # which does not allow to call GetReachValues. This does not work
    # >>> values = test_file.get_reach_values("10", 0, "SWMM_LINK_FLOW")
    # >>> time_series = pd.Series(values, index=test_file.time_index)
    # >>> assert len(values) == 36
    # >>> assert len(time_series.index) == 36

    # Just try to call the methods
    test_file.get_reach_end_values("10", "SWMM_LINK_FLOW")
    test_file.get_reach_start_values("10", "SWMM_LINK_FLOW")
    test_file.get_reach_sum_values("10", "SWMM_LINK_FLOW")


def test_get_reach_value(test_file):
    # Does not work from MIKE 1D side.
    # >>> value = test_file.get_reach_value("10", 0, "SWMM_LINK_FLOW", test_file.start_time)
    # >>> assert value > 0
    assert 0 == 0


def test_dotnet_methods(test_file):
    epanet_res = test_file
    epanet_res.data.ResultSpecs
    epanet_res.data.Nodes

    assert pytest.approx(0.003947457) == epanet_res.query.GetNodeValues("9", "SWMM_NODE_DEPTH")[20]

    # Does not work from MIKE 1D side.
    # >>> epanet_res.query.GetReachValue("10", 0, "SWMM_LINK_FLOW", epanet_res.data.StartTime)
    # >>> epanet_res.query.GetReachValues("10", 0, "SWMM_LINK_FLOW")

    assert pytest.approx(0.000736411) == epanet_res.query.GetReachEndValues("10", "SWMM_LINK_FLOW")[20]
    assert pytest.approx(0.000736411) == epanet_res.query.GetReachStartValues("10", "SWMM_LINK_FLOW")[20]
    assert pytest.approx(0.000736411) == epanet_res.query.GetReachSumValues("10", "SWMM_LINK_FLOW")[20]


def test_epanet_res_filter(test_file_path):
    nodes = ["9", "10"]
    reaches = ["10"]
    epanet_res = Res1D(test_file_path, nodes=nodes, reaches=reaches)

    epanet_res.read(QueryDataReach("SWMM_LINK_FLOW", "10"))
    epanet_res.read(QueryDataNode("SWMM_NODE_DEPTH", "9"))
    epanet_res.read(QueryDataNode("SWMM_NODE_DEPTH", "10"))

    # Currently Mike1D raises System.ArgumentOutOfRangeException when requesting location not included by filter
    # This should be fixed in Mike1D to raise more meaningful Mike1DException
    with pytest.raises(Exception):
        assert epanet_res.read(QueryDataReach("SWMM_LINK_FLOW", "10xyz"))

    with pytest.raises(NoDataForQuery):
        assert epanet_res.read(QueryDataNode("SWMM_NODE_DEPTH", "10xyz"))


def test_epanet_res_filter_readall(test_file_path):
    # Make sure read all can be used with filters
    nodes = ["9", "10"]
    reaches = ["10"]
    epanet_res = Res1D(test_file_path, nodes=nodes, reaches=reaches)

    epanet_res.read()
