import os
import pytest
import numpy as np

from mikeio1d.custom_exceptions import NoDataForQuery, InvalidQuantity
from mikeio1d.res1d import Res1D
from mikeio1d.query import QueryDataReach
from mikeio1d.query import QueryDataNode
from mikeio1d.dotnet import to_numpy


@pytest.fixture
def test_file_path():
    test_folder_path = os.path.dirname(os.path.abspath(__file__))
    # Original file name was Exam6Base.epanet_res
    return os.path.join(test_folder_path, "testdata", "epanet.res")


@pytest.fixture(params=[False])
def test_file(test_file_path, request):
    return Res1D(test_file_path, lazy_load=request.param)


def test_read(test_file):
    df = test_file.read()
    assert len(df) == 25
    # TODO: assert not df.columns.duplicated().any() - add this, but it fails since columns are not guaranteed unique


def test_quantities(test_file):
    quantities = test_file.quantities
    assert len(quantities) == 12


def test_info(test_file):
    epanet_res = test_file
    epanet_res_info = epanet_res._get_info()
    epanet_res_info_ref = (
        "Start time: 2022-10-13 00:00:00\n"
        + "End time: 2022-10-14 00:00:00\n"
        + "# Timesteps: 25\n"
        + "# Catchments: 0\n"
        + "# Nodes: 11\n"
        + "# Reaches: 13\n"
        + "# Globals: 0\n"
        + "0 - Demand <l/s>\n"
        + "1 - Head <m>\n"
        + "2 - Pressure <m>\n"
        + "3 - WaterQuality <->\n"
        + "4 - Flow <l/s>\n"
        + "5 - Velocity <m/s>\n"
        + "6 - HeadlossPer1000Unit <m>\n"
        + "7 - AvgWaterQuality <->\n"
        + "8 - StatusCode <->\n"
        + "9 - Setting <->\n"
        + "10 - ReactorRate <->\n"
        + "11 - FrictionFactor <->"
    )

    assert epanet_res_info == epanet_res_info_ref


def test_data_item_dicts(test_file):
    epanet_res = test_file
    assert len(epanet_res.catchments) == 0
    assert len(epanet_res.nodes) == 11
    assert len(epanet_res.reaches) == 13
    assert len(epanet_res.global_data) == 0


@pytest.mark.parametrize(
    "query,expected",
    [
        (QueryDataReach("Flow", "10"), True),
        (QueryDataReach("Flow", "10xyz"), False),
        (QueryDataReach("Flow", "wrong_reach_name"), False),
    ],
)
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


@pytest.mark.parametrize(
    "query,expected_max",
    [
        (QueryDataReach("Flow", "10"), 120.466),
        (QueryDataReach("Flow", "12"), 16.268),
        (QueryDataReach("FrictionFactor", "10"), 0.032),
        (QueryDataReach("FrictionFactor", "12"), 0.047),
    ],
)
def test_read_reach_with_queries(test_file, query, expected_max):
    data = test_file.read(query)
    assert pytest.approx(round(data.max().values[0], 3)) == expected_max


@pytest.mark.parametrize(
    "quantity,reach_id,expected_max",
    [
        ("Flow", "10", 120.466),
        ("Flow", "12", 16.268),
        ("FrictionFactor", "10", 0.032),
        ("FrictionFactor", "12", 0.047),
    ],
)
def test_read_reach(test_file, quantity, reach_id, expected_max):
    data = test_file.query.GetReachStartValues(reach_id, quantity)
    data = to_numpy(data)
    actual_max = round(np.max(data), 3)
    assert pytest.approx(actual_max) == expected_max


@pytest.mark.parametrize(
    "quantity,node_id,expected_max", [("Pressure", "10", 94.181), ("Pressure", "11", 88.970)]
)
def test_read_node(test_file, quantity, node_id, expected_max):
    data = test_file.query.GetNodeValues(node_id, quantity)
    data = to_numpy(data)
    actual_max = round(np.max(data), 3)
    assert pytest.approx(actual_max) == expected_max


def test_time_index(test_file):
    assert len(test_file.time_index) == 25


def test_start_time(test_file):
    assert test_file.start_time == test_file.time_index.min()


def test_get_node_values(test_file):
    values = test_file.get_node_values("10", "Pressure")
    assert len(values) == 25


def test_get_reach_values(test_file):
    # When reading EPANET results there is a bug in MIKE 1D,
    # which does not allow to call GetReachValues. This does not work
    # >>> values = test_file.get_reach_values("10", 0, "Flow")
    # >>> time_series = pd.Series(values, index=test_file.time_index)
    # >>> assert len(values) == 25
    # >>> assert len(time_series.index) == 25

    # Just try to call the methods
    test_file.get_reach_end_values("10", "Flow")
    test_file.get_reach_start_values("10", "Flow")
    test_file.get_reach_sum_values("10", "Flow")


def test_get_reach_value(test_file):
    # Does not work from MIKE 1D side.
    # >>> value = test_file.get_reach_value("10", 0, "Flow", test_file.start_time)
    # >>> assert value > 0
    assert 0 == 0


def test_dotnet_methods(test_file):
    epanet_res = test_file
    epanet_res.data.ResultSpecs
    epanet_res.data.Nodes

    assert pytest.approx(89.717) == epanet_res.query.GetNodeValues("10", "Pressure")[0]

    # Does not work from MIKE 1D side.
    # >>> epanet_res.query.GetReachValue("10", 0, "Flow", epanet_res.data.StartTime)
    # >>> epanet_res.query.GetReachValues("10", 0, "Flow")

    assert pytest.approx(77.8665) == epanet_res.query.GetReachEndValues("11", "Flow")[0]
    assert pytest.approx(77.8665) == epanet_res.query.GetReachStartValues("11", "Flow")[0]
    assert pytest.approx(77.8665) == epanet_res.query.GetReachSumValues("11", "Flow")[0]


def test_epanet_res_filter(test_file_path, helpers):
    nodes = ["10", "11"]
    reaches = ["11"]
    epanet_res = Res1D(test_file_path, nodes=nodes, reaches=reaches)

    df_flow_10 = epanet_res.read(QueryDataReach("Flow", "10"))
    df_pressures_10 = epanet_res.read(QueryDataNode("Pressure", "10"))
    df_pressure_11 = epanet_res.read(QueryDataNode("Pressure", "11"))

    epanet_res_full = Res1D(test_file_path)
    df_full = epanet_res_full.read()

    helpers.assert_shared_columns_equal(df_full, df_flow_10)
    helpers.assert_shared_columns_equal(df_full, df_pressures_10)
    helpers.assert_shared_columns_equal(df_full, df_pressure_11)

    # Currently Mike1D raises System.ArgumentOutOfRangeException when requesting location not included by filter
    # This should be fixed in Mike1D to raise more meaningful Mike1DException
    with pytest.raises(Exception):
        assert epanet_res.read(QueryDataReach("Flow", "10xyz"))

    with pytest.raises(NoDataForQuery):
        assert epanet_res.read(QueryDataNode("Pressure", "10xyz"))


def test_epanet_res_filter_readall(test_file_path, helpers):
    # Make sure read all can be used with filters
    nodes = ["10", "11"]
    reaches = ["11"]
    epanet_res = Res1D(test_file_path, nodes=nodes, reaches=reaches)
    df = epanet_res.read()

    epanet_res_full = Res1D(test_file_path)
    df_full = epanet_res_full.read()

    helpers.assert_shared_columns_equal(df_full, df)
