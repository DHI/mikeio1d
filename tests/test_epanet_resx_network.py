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
    # Original file name was Exam6Base.epanet_resx
    return os.path.join(test_folder_path, "testdata", "epanet.resx")


@pytest.fixture(params=[False])
def test_file(test_file_path, request):
    return Res1D(test_file_path, lazy_load=request.param)


def test_read(test_file):
    df = test_file.read()
    assert len(df) == 25
    # TODO: assert not df.columns.duplicated().any() - add this, but it fails since columns are not guaranteed unique


def test_quantities(test_file):
    quantities = test_file.quantities
    assert len(quantities) == 5


def test_info(test_file):
    epanet_resx = test_file
    epanet_resx_info = epanet_resx._get_info()
    epanet_repr_ref = (
        "Start time: 2022-10-13 00:00:00\n"
        + "End time: 2022-10-14 00:00:00\n"
        + "# Timesteps: 25\n"
        + "# Catchments: 0\n"
        + "# Nodes: 2\n"
        + "# Reaches: 1\n"
        + "# Globals: 0\n"
        + "0 - Volume <m^3>\n"
        + "1 - Volume Percentage <%>\n"
        + "2 - Pump efficiency <%>\n"
        + "3 - Pump energy costs </kWh>\n"
        + "4 - Pump energy <kW>"
    )
    assert epanet_resx_info == epanet_repr_ref


def test_data_item_dicts(test_file):
    epanet_resx = test_file
    assert len(epanet_resx.catchments) == 0
    assert len(epanet_resx.nodes) == 2
    assert len(epanet_resx.reaches) == 1
    assert len(epanet_resx.global_data) == 0


@pytest.mark.parametrize(
    "query,expected",
    [
        (QueryDataReach("Pump energy", "9"), True),
        (QueryDataReach("Pump energy", "10xyz"), False),
        (QueryDataReach("Pump energy", "wrong_reach_name"), False),
    ],
)
def test_valid_reach_data_queries(test_file, query, expected):
    epanet_resx = test_file

    with pytest.raises(InvalidQuantity):
        invalid_query = QueryDataReach("InvalidQuantity", "9")
        assert epanet_resx.read(invalid_query)

    if expected:
        epanet_resx.read(query)
    else:
        with pytest.raises(Exception):
            assert epanet_resx.read(query)


@pytest.mark.parametrize(
    "query,expected_max",
    [
        (QueryDataReach("Pump energy", "9"), 96.707),
        (QueryDataReach("Pump energy costs", "9"), 0.0),
        (QueryDataReach("Pump efficiency", "9"), 75.0),
    ],
)
def test_read_reach_with_queries(test_file, query, expected_max):
    data = test_file.read(query)
    assert pytest.approx(round(data.max().values[0], 3)) == expected_max


@pytest.mark.parametrize(
    "quantity,reach_id,expected_max",
    [("Pump energy", "9", 96.707), ("Pump energy costs", "9", 0.0), ("Pump efficiency", "9", 75.0)],
)
def test_read_reach(test_file, quantity, reach_id, expected_max):
    data = test_file.query.GetReachStartValues(reach_id, quantity)
    data = to_numpy(data)
    actual_max = round(np.max(data), 3)
    assert pytest.approx(actual_max) == expected_max


@pytest.mark.parametrize(
    "quantity,node_id,expected_max", [("Volume", "2", 7859.459), ("Volume Percentage", "2", 92.381)]
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
    values = test_file.get_node_values("9", "Volume")
    assert len(values) == 25


def test_get_reach_values(test_file):
    # When reading EPANET results there is a bug in MIKE 1D,
    # which does not allow to call GetReachValues. This does not work
    # >>> values = test_file.get_reach_values("9", 0, "Pump energy")
    # >>> time_series = pd.Series(values, index=test_file.time_index)
    # >>> assert len(values) == 25
    # >>> assert len(time_series.index) == 25

    # Just try to call the methods
    test_file.get_reach_end_values("9", "Pump energy")
    test_file.get_reach_start_values("9", "Pump energy")
    test_file.get_reach_sum_values("9", "Pump energy")


def test_get_reach_value(test_file):
    # Does not work from MIKE 1D side.
    # >>> value = test_file.get_reach_value("9", 0, "Pump energy", test_file.start_time)
    # >>> assert value > 0
    assert 0 == 0


def test_dotnet_methods(test_file):
    epanet_resx = test_file
    epanet_resx.data.ResultSpecs
    epanet_resx.data.Nodes

    assert pytest.approx(6806.107) == epanet_resx.query.GetNodeValues("2", "Volume")[0]

    # Does not work from MIKE 1D side.
    # >>> epanet_resx.query.GetReachValue("9", 0, "Pump energy", epanet_resx.data.StartTime)
    # >>> epanet_resx.query.GetReachValues("9", 0, "Pump energy")

    assert pytest.approx(95.8442) == epanet_resx.query.GetReachEndValues("9", "Pump energy")[0]
    assert pytest.approx(95.8442) == epanet_resx.query.GetReachStartValues("9", "Pump energy")[0]
    assert pytest.approx(95.8442) == epanet_resx.query.GetReachSumValues("9", "Pump energy")[0]


def test_epanet_resx_filter(test_file_path, helpers):
    nodes = ["2", "9"]
    reaches = ["9"]
    epanet_resx = Res1D(test_file_path, nodes=nodes, reaches=reaches)

    df_energy_9 = epanet_resx.read(QueryDataReach("Pump energy", "9"))
    df_volume_2 = epanet_resx.read(QueryDataNode("Volume", "2"))
    df_volume_9 = epanet_resx.read(QueryDataNode("Volume", "9"))

    epanet_resx_full = Res1D(test_file_path)
    df_full = epanet_resx_full.read()

    helpers.assert_shared_columns_equal(df_full, df_energy_9)
    helpers.assert_shared_columns_equal(df_full, df_volume_2)
    helpers.assert_shared_columns_equal(df_full, df_volume_9)

    # Currently Mike1D raises System.ArgumentOutOfRangeException when requesting location not included by filter
    # This should be fixed in Mike1D to raise more meaningful Mike1DException
    with pytest.raises(Exception):
        assert epanet_resx.read(QueryDataReach("Pump energy", "10xyz"))

    with pytest.raises(NoDataForQuery):
        assert epanet_resx.read(QueryDataNode("Volume", "10xyz"))


def test_epanet_resx_filter_readall(test_file_path, helpers):
    # Make sure read all can be used with filters
    nodes = ["2", "9"]
    reaches = ["9"]
    epanet_resx = Res1D(test_file_path, nodes=nodes, reaches=reaches)
    df = epanet_resx.read()

    epanet_resx_full = Res1D(test_file_path)
    df_full = epanet_resx_full.read()

    helpers.assert_shared_columns_equal(df_full, df)
