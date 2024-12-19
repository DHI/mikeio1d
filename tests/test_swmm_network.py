import os
import pytest
import numpy as np

from mikeio1d.custom_exceptions import NoDataForQuery, InvalidQuantity
from mikeio1d.res1d import Res1D
from mikeio1d.query import QueryDataReach
from mikeio1d.query import QueryDataNode
from mikeio1d.dotnet import to_numpy
from mikeio1d.result_reader_writer.result_reader import ColumnMode


@pytest.fixture
def test_file_path():
    test_folder_path = os.path.dirname(os.path.abspath(__file__))
    # Original file name was Exam6Base.swmm_out
    return os.path.join(test_folder_path, "testdata", "swmm.out")


@pytest.fixture(params=[False])
def test_file(test_file_path, request):
    return Res1D(test_file_path, lazy_load=request.param)


def test_read(test_file):
    df = test_file.read()
    assert len(df) == 36
    # TODO: assert not df.columns.duplicated().any() - add this, but it fails since columns are not guaranteed unique


def test_quantities(test_file):
    quantities = test_file.quantities
    assert len(quantities) == 36


def test_info(test_file):
    swmm_out = test_file
    swmm_out.info()


def test_data_item_dicts(test_file):
    swmm_out = test_file
    assert len(swmm_out.catchments) == 8
    assert len(swmm_out.nodes) == 14
    assert len(swmm_out.reaches) == 13
    assert len(swmm_out.global_data) == 14


@pytest.mark.parametrize(
    "query,expected",
    [
        (QueryDataReach("SWMM_LINK_FLOW", "10"), True),
        (QueryDataReach("SWMM_LINK_FLOW", "10xyz"), False),
        (QueryDataReach("SWMM_LINK_FLOW", "wrong_reach_name"), False),
    ],
)
def test_valid_reach_data_queries(test_file, query, expected):
    swmm_out = test_file

    with pytest.raises(InvalidQuantity):
        invalid_query = QueryDataReach("InvalidQuantity", "10")
        assert swmm_out.read(invalid_query)

    if expected:
        swmm_out.read(query)
    else:
        with pytest.raises(Exception):
            assert swmm_out.read(query)


@pytest.mark.parametrize(
    "query,expected_max",
    [
        (QueryDataReach("SWMM_LINK_FLOW", "10"), 18.204),
        (QueryDataReach("SWMM_LINK_FLOW", "12"), 2.43),
        (QueryDataReach("SWMM_LINK_DEPTH", "10"), 1.063),
        (QueryDataReach("SWMM_LINK_DEPTH", "12"), 0.462),
    ],
)
def test_read_reach_with_queries(test_file, query, expected_max):
    data = test_file.read(query)
    assert pytest.approx(round(data.max().values[0], 3)) == expected_max


@pytest.mark.parametrize(
    "quantity,reach_id,expected_max",
    [
        ("SWMM_LINK_FLOW", "10", 18.204),
        ("SWMM_LINK_FLOW", "12", 2.43),
        ("SWMM_LINK_DEPTH", "10", 1.063),
        ("SWMM_LINK_DEPTH", "12", 0.462),
    ],
)
def test_read_reach(test_file, quantity, reach_id, expected_max):
    data = test_file.query.GetReachStartValues(reach_id, quantity)
    data = to_numpy(data)
    actual_max = round(np.max(data), 3)
    assert pytest.approx(actual_max) == expected_max


@pytest.mark.parametrize(
    "quantity,node_id,expected_max",
    [("SWMM_NODE_DEPTH", "9", 0.568), ("SWMM_NODE_DEPTH", "10", 3.0)],
)
def test_read_node(test_file, quantity, node_id, expected_max):
    data = test_file.query.GetNodeValues(node_id, quantity)
    data = to_numpy(data)
    actual_max = round(np.max(data), 3)
    assert pytest.approx(actual_max) == expected_max


def test_time_index(test_file):
    assert len(test_file.time_index) == 36


def test_start_time(test_file):
    assert test_file.start_time == test_file.time_index.min()


def test_get_reach_value(test_file):
    # Does not work from MIKE 1D side.
    # >>> value = test_file.get_reach_value("10", 0, "SWMM_LINK_FLOW", test_file.start_time)
    # >>> assert value > 0
    assert 0 == 0


def test_dotnet_methods(test_file):
    swmm_out = test_file
    swmm_out.data.ResultSpecs
    swmm_out.data.Nodes

    assert pytest.approx(0.003947457) == swmm_out.query.GetNodeValues("9", "SWMM_NODE_DEPTH")[20]

    # Does not work from MIKE 1D side.
    # >>> swmm_out.query.GetReachValue("10", 0, "SWMM_LINK_FLOW", swmm_out.data.StartTime)
    # >>> swmm_out.query.GetReachValues("10", 0, "SWMM_LINK_FLOW")

    assert (
        pytest.approx(0.000736411) == swmm_out.query.GetReachEndValues("10", "SWMM_LINK_FLOW")[20]
    )
    assert (
        pytest.approx(0.000736411) == swmm_out.query.GetReachStartValues("10", "SWMM_LINK_FLOW")[20]
    )
    assert (
        pytest.approx(0.000736411) == swmm_out.query.GetReachSumValues("10", "SWMM_LINK_FLOW")[20]
    )


def test_swmm_out_filter(test_file_path, helpers):
    nodes = ["9", "10"]
    reaches = ["10"]
    swmm_out = Res1D(test_file_path, nodes=nodes, reaches=reaches)
    swmm_out.reader.column_mode = ColumnMode.ALL

    df_flow_10 = swmm_out.read(QueryDataReach("SWMM_LINK_FLOW", "10"))
    df_depth_9 = swmm_out.read(QueryDataNode("SWMM_NODE_DEPTH", "9"))
    df_depth_10 = swmm_out.read(QueryDataNode("SWMM_NODE_DEPTH", "10"))

    swmm_out_full = Res1D(test_file_path)
    swmm_out_full.reader.column_mode = ColumnMode.ALL
    df_full = swmm_out_full.read()

    helpers.assert_shared_columns_equal(df_full, df_flow_10)
    helpers.assert_shared_columns_equal(df_full, df_depth_9)
    helpers.assert_shared_columns_equal(df_full, df_depth_10)

    # Currently Mike1D raises System.ArgumentOutOfRangeException when requesting location not included by filter
    # This should be fixed in Mike1D to raise more meaningful Mike1DException
    with pytest.raises(Exception):
        assert swmm_out.read(QueryDataReach("SWMM_LINK_FLOW", "10xyz"))

    with pytest.raises(NoDataForQuery):
        assert swmm_out.read(QueryDataNode("SWMM_NODE_DEPTH", "10xyz"))


def test_swmm_out_filter_readall(test_file_path, helpers):
    # Make sure read all can be used with filters
    nodes = ["9", "10"]
    reaches = ["10"]
    swmm_out = Res1D(test_file_path, nodes=nodes, reaches=reaches)
    df = swmm_out.read()

    swmm_out_full = Res1D(test_file_path)
    df_full = swmm_out_full.read()

    helpers.assert_shared_columns_equal(df_full, df)
