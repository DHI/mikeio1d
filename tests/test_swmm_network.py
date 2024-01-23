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
    swmm_out_info = swmm_out._get_info()
    swmm_out_info_ref = (
        "Start time: 1998-01-01 01:00:00.001000\n"
        + "End time: 1998-01-02 12:00:00.001000\n"
        + "# Timesteps: 36\n"
        + "# Catchments: 8\n"
        + "# Nodes: 14\n"
        + "# Reaches: 13\n"
        + "# Globals: 15\n"
        + "0 - SWMM_NODE_DEPTH <ft>\n"
        + "1 - SWMM_NODE_HEAD <ft>\n"
        + "2 - SWMM_NODE_VOLUME <ft^3>\n"
        + "3 - SWMM_NODE_LATFLOW <ft^3/s>\n"
        + "4 - SWMM_NODE_INFLOW <ft^3/s>\n"
        + "5 - SWMM_NODE_OVERFLOW <ft^3/s>\n"
        + "6 - SWMM_NODE_QUAL <mu-g/l>\n"
        + "7 - SWMM_LINK_FLOW <ft^3/s>\n"
        + "8 - SWMM_LINK_DEPTH <ft>\n"
        + "9 - SWMM_LINK_VELOCITY <ft/s>\n"
        + "10 - SWMM_LINK_Froude_Number <()>\n"
        + "11 - SWMM_LINK_CAPACITY <()>\n"
        + "12 - SWMM_LINK_QUAL <mu-g/l>\n"
        + "13 - SWMM_SUBCATCH_RAINFALL <in/h>\n"
        + "14 - SWMM_SUBCATCH_SNOWDEPTH <in>\n"
        + "15 - SWMM_SUBCATCH_EVAP <in>\n"
        + "16 - SWMM_SUBCATCH_INFIL <in/h>\n"
        + "17 - SWMM_SUBCATCH_RUNOFF <ft^3/s>\n"
        + "18 - SWMM_SUBCATCH_GW_FLOW <ft^3/s>\n"
        + "19 - SWMM_SUBCATCH_GW_ELEV <ft>\n"
        + "20 - SWMM_SUBCATCH_SOIL_MOIST <()>\n"
        + "21 - SWMM_SUBCATCH_WASHOFF <mu-g/l>\n"
        + "22 - SWMM_SYS_TEMPERATURE <deg F>\n"
        + "23 - SWMM_SYS_RAINFALL <in/h>\n"
        + "24 - SWMM_SYS_SNOWDEPTH <in>\n"
        + "25 - SWMM_SYS_INFIL <in/h>\n"
        + "26 - SWMM_SYS_RUNOFF <ft^3/s>\n"
        + "27 - SWMM_SYS_DWFLOW <ft^3/s>\n"
        + "28 - SWMM_SYS_GWFLOW <ft^3/s>\n"
        + "29 - SWMM_SYS_INFLOW <ft^3/s>\n"
        + "30 - SWMM_SYS_EXFLOW <ft^3/s>\n"
        + "31 - SWMM_SYS_FLOODING <ft^3/s>\n"
        + "32 - SWMM_SYS_OUTFLOW <ft^3/s>\n"
        + "33 - SWMM_SYS_STORAGE <ft^3>\n"
        + "34 - SWMM_SYS_EVAP <->\n"
        + "35 - SWMM_SYS_PET <->"
    )
    assert swmm_out_info == swmm_out_info_ref


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
    swmm_out.result_reader.column_mode = ColumnMode.ALL

    df_flow_10 = swmm_out.read(QueryDataReach("SWMM_LINK_FLOW", "10"))
    df_depth_9 = swmm_out.read(QueryDataNode("SWMM_NODE_DEPTH", "9"))
    df_depth_10 = swmm_out.read(QueryDataNode("SWMM_NODE_DEPTH", "10"))

    swmm_out_full = Res1D(test_file_path)
    swmm_out_full.result_reader.column_mode = ColumnMode.ALL
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
