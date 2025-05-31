import os
import pytest
import numpy as np
import pandas as pd

from mikeio1d.custom_exceptions import NoDataForQuery, InvalidQuantity
from mikeio1d.res1d import Res1D
from mikeio1d.various import mike1d_quantities
from mikeio1d.query import QueryDataReach
from mikeio1d.query import QueryDataNode
from mikeio1d.dotnet import to_numpy
from mikeio1d.result_reader_writer.result_reader import ColumnMode


@pytest.fixture
def test_file_path():
    test_folder_path = os.path.dirname(os.path.abspath(__file__))
    # Original file name was Exam6Base.res1d
    return os.path.join(test_folder_path, "testdata", "network.res1d")


@pytest.fixture
def test_file(test_file_path):
    return Res1D(test_file_path, lazy_load=False)


def test_file_does_not_exist():
    with pytest.raises(FileExistsError):
        assert Res1D("tests/testdata/not_a_file.res1d")


def test_read(test_file):
    df = test_file.read()
    assert len(df) == 110
    assert not df.columns.duplicated().any()


def test_mike1d_quantities():
    quantities = mike1d_quantities()
    assert "WaterLevel" in quantities


def test_mike1d_result_type(test_file):
    assert test_file.result_type == "HDRR"


def test_quantities(test_file):
    quantities = test_file.quantities
    assert len(quantities) == 2


def test_info(test_file):
    res1d = test_file
    res1d_info = res1d._get_info()
    res1d_info_ref = (
        "Start time: 1994-08-07 16:35:00\n"
        "End time: 1994-08-07 18:35:00\n"
        "# Timesteps: 110\n"
        "# Catchments: 0\n"
        "# Nodes: 119\n"
        "# Reaches: 118\n"
        "# Globals: 0\n"
        "0 - Water level (m)\n"
        "1 - Discharge (m^3/s)"
    )
    assert res1d_info == res1d_info_ref


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


def test_time_index_microseconds(test_file):
    df = test_file.read()
    assert df.index.microsecond.unique().size > 1


def test_dotnet_methods(test_file):
    res1d = test_file
    # Just try to access the properties and methods in .net
    res1d.result_data.ResultSpecs
    res1d.result_data.Nodes
    res1d.query.GetNodeValues("1", "WaterLevel")
    res1d.query.GetReachValue(
        "9l1", 5, "WaterLevel", res1d.result_data.StartTime
    )  # must be dotnet datetime
    res1d.query.GetReachValues("9l1", 5, "WaterLevel")
    res1d.query.GetReachEndValues("9l1", "WaterLevel")  # avoid specifying chainage
    res1d.query.GetReachStartValues("9l1", "WaterLevel")  # avoid specifying chainage
    res1d.query.GetReachSumValues(
        "9l1", "WaterLevel"
    )  # useful for summing volume in reach (all grid points)


def test_res1d_filter(test_file_path, helpers):
    nodes = ["1", "2"]
    reaches = ["9l1"]
    res1d = Res1D(test_file_path, nodes=nodes, reaches=reaches)
    res1d.reader.column_mode = ColumnMode.ALL

    df_9l1 = res1d.read(QueryDataReach("WaterLevel", "9l1", 10))
    df_1 = res1d.read(QueryDataNode("WaterLevel", "1"))
    df_2 = res1d.read(QueryDataNode("WaterLevel", "2"))

    res1d_full = Res1D(test_file_path)
    res1d_full.reader.column_mode = ColumnMode.ALL
    df_full = res1d_full.read()

    helpers.assert_shared_columns_equal(df_full, df_9l1)
    helpers.assert_shared_columns_equal(df_full, df_1)
    helpers.assert_shared_columns_equal(df_full, df_2)

    # Currently Mike1D raises NullReferenceException when requesting location not included by filter
    # This should be fixed in Mike1D to raise more meaningful Mike1DException
    # with pytest.raises(Exception):
    #     assert res1d.read(QueryDataReach("WaterLevel", "100l1", 10))
    #     assert res1d.read(QueryDataNode("WaterLevel", "3"))


def test_res1d_filter_readall(test_file_path, helpers):
    # Make sure read all can be used with filters
    nodes = ["1", "2"]
    reaches = ["9l1"]
    res1d = Res1D(test_file_path, nodes=nodes, reaches=reaches)
    df = res1d.read()

    res1d_full = Res1D(test_file_path)
    df_full = res1d_full.read()

    helpers.assert_shared_columns_equal(df_full, df)


def test_res1d_filter_using_flow_split(flow_split_file_path, helpers):
    res1d_full = Res1D(flow_split_file_path)
    df_full = res1d_full.read(column_mode=ColumnMode.ALL)

    for node in res1d_full.nodes:
        res1d = Res1D(flow_split_file_path, nodes=[str(node)])
        df = res1d.read(column_mode=ColumnMode.ALL)
        helpers.assert_shared_columns_equal(df_full, df)

    for reach in res1d_full.reaches:
        res1d = Res1D(flow_split_file_path, reaches=[str(reach)])
        df = res1d.read(column_mode=ColumnMode.ALL)
        helpers.assert_shared_columns_equal(df_full, df)


@pytest.mark.parametrize(
    "time, expected_len, expected_start, expected_end",
    [
        (
            None,
            110,
            "1994-08-07 16:35:00.000",
            "1994-08-07 18:35:00.000",
        ),
        (
            slice("1994-08-07 16:35:00.000", "1994-08-07 16:37:07.560000"),
            3,
            "1994-08-07 16:35:00.000",
            "1994-08-07 16:37:07.560000",
        ),
        (
            ("1994-08-07 16:35:00.000", "1994-08-07 16:37:07.560000"),
            3,
            "1994-08-07 16:35:00.000",
            "1994-08-07 16:37:07.560000",
        ),
        (
            slice(None, "1994-08-07 16:37:07.560000"),
            3,
            "1994-08-07 16:35:00.000",
            "1994-08-07 16:37:07.560000",
        ),
        (
            (None, "1994-08-07 16:37:07.560000"),
            3,
            "1994-08-07 16:35:00.000",
            "1994-08-07 16:37:07.560000",
        ),
        (
            slice("1994-08-07 18:32:07.967000", None),
            3,
            "1994-08-07 18:32:07.967000",
            "1994-08-07 18:35:00.000",
        ),
        (
            ("1994-08-07 18:32:07.967000", None),
            3,
            "1994-08-07 18:32:07.967000",
            "1994-08-07 18:35:00.000",
        ),
        (
            [
                slice("1994-08-07 16:35:00.000", "1994-08-07 16:38:00.000000"),
                slice("1994-08-07 16:38:00.000", "1994-08-07 16:48:00.000000"),
                slice("1994-08-07 16:48:00.000", "1994-08-07 16:58:12.888000"),
            ],
            21,
            "1994-08-07 16:35:00.000",
            "1994-08-07 16:58:12.888000",
        ),
        (
            [
                slice("1994-08-07 16:35:00.000", "1994-08-07 16:37:07.560000"),
                slice("1994-08-07 16:45:00.000", "1994-08-07 16:48:00.000000"),
                slice("1994-08-07 16:55:00.000", "1994-08-07 16:58:12.888000"),
            ],
            9,
            "1994-08-07 16:35:00.000",
            "1994-08-07 16:58:12.888000",
        ),
        (
            [
                ("1994-08-07 16:35:00.000", "1994-08-07 16:37:07.560000"),
                ("1994-08-07 16:45:00.000", "1994-08-07 16:48:00.000000"),
                ("1994-08-07 16:55:00.000", "1994-08-07 16:58:12.888000"),
            ],
            9,
            "1994-08-07 16:35:00.000",
            "1994-08-07 16:58:12.888000",
        ),
    ],
)
def test_res1d_filter_time(test_file_path, time, expected_len, expected_start, expected_end):
    expected_start = pd.Timestamp(expected_start)
    expected_end = pd.Timestamp(expected_end)

    res1d = Res1D(test_file_path, time=time)

    res1d.reader.load_dynamic_data()
    assert res1d.result_data.NumberOfTimeSteps == expected_len
    assert res1d.time_index[0] == expected_start
    assert res1d.time_index[-1] == expected_end


@pytest.mark.parametrize("step_every", [1, 2, 3])
def test_res1d_filter_step_every(test_file_path, step_every):
    res1d = Res1D(test_file_path, step_every=step_every)

    start_time_step = 0
    max_time_step = 110
    expected_steps = len(range(start_time_step, max_time_step, step_every))

    res1d.reader.load_dynamic_data()
    assert res1d.data.NumberOfTimeSteps == expected_steps


def test_res1d_filter_quantity_invalid_id(test_file_path):
    with pytest.raises(ValueError):
        Res1D(test_file_path, quantities=["InvalidQuantity"])


@pytest.mark.parametrize("quantities", [["WaterLevel"], ["WaterLevel", "Discharge"]])
def test_res1d_filter_quantity(test_file_path, quantities):
    res = Res1D(test_file_path, quantities=quantities)

    quantities = set(quantities)
    assert quantities.issuperset(set(res.nodes.quantities))
    assert quantities.issuperset(set(res.catchments.quantities))
    assert quantities.issuperset(set(res.structures.quantities))
    assert quantities.issuperset(set(res.reaches.quantities.keys()))
    assert quantities.issuperset(set(res.reaches[res.reaches.names[0]].quantities))


def test_node_attributes(test_file):
    res1d = test_file
    nodes = res1d.nodes

    nodes.n_1.WaterLevel.add()
    nodes.n_2.WaterLevel.add()
    df = res1d.read()

    column_mode = res1d.reader.column_mode

    if column_mode in (ColumnMode.ALL, ColumnMode.COMPACT):
        actual_max = round(df.T.query("quantity=='WaterLevel' and name=='1'").T.max(), 3)
    elif column_mode == ColumnMode.STRING:
        actual_max = round(df["WaterLevel:1"].max(), 3)
    assert pytest.approx(actual_max) == 195.669

    if column_mode in (ColumnMode.ALL, ColumnMode.COMPACT):
        actual_max = round(df.T.query("quantity=='WaterLevel' and name=='2'").T.max(), 3)
    elif column_mode == ColumnMode.STRING:
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

    column_mode = res1d.reader.column_mode

    if column_mode in (ColumnMode.ALL, ColumnMode.COMPACT):
        actual_max = round(
            df.T.query("quantity=='WaterLevel' and name=='104l1' and chainage==34.4131").T.max(), 3
        )
    elif column_mode == ColumnMode.STRING:
        actual_max = round(df["WaterLevel:104l1:34.4131"].max(), 3)
    assert pytest.approx(actual_max) == 197.046

    if column_mode in (ColumnMode.ALL, ColumnMode.COMPACT):
        actual_max = round(
            df.T.query("quantity=='WaterLevel' and name=='9l1' and chainage==10").T.max(), 3
        )
    elif column_mode == ColumnMode.STRING:
        actual_max = round(df["WaterLevel:9l1:10"].max(), 3)
    assert pytest.approx(actual_max) == 195.165

    if column_mode in (ColumnMode.ALL, ColumnMode.COMPACT):
        actual_max = round(
            df.T.query("quantity=='Discharge' and name=='100l1' and chainage==23.8414").T.max(), 3
        )
    elif column_mode == ColumnMode.STRING:
        actual_max = round(df["Discharge:100l1:23.8414"].max(), 3)
    assert pytest.approx(actual_max) == 0.1

    if column_mode in (ColumnMode.ALL, ColumnMode.COMPACT):
        actual_max = round(
            df.T.query("quantity=='Discharge' and name=='9l1' and chainage==5").T.max(), 3
        )
    elif column_mode == ColumnMode.STRING:
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


def test_structure_reach_static_attributes_exist(res1d_network, res1d_river_network):
    for network in [res1d_network, res1d_river_network]:
        for _, structure in network.structures.items():
            assert hasattr(structure, "id")
            assert hasattr(structure, "type")
            assert hasattr(structure, "chainage")


def test_structure_reach_static_attributes(res1d_network):
    structures = res1d_network.structures

    assert structures.s_119w1.type == "Weir"
    assert structures.s_119w1.id == "119w1"
    assert structures.s_119w1.chainage == pytest.approx(0.5)

    assert structures.s_115p1.type == "Pump"
    assert structures.s_115p1.id == "115p1"
    assert structures.s_115p1.chainage == pytest.approx(41.21402714094492)


def test_to_dataframe_aliases(res1d_network):
    """Test that to_dataframe() alias exists and returns a DataFrame in all relevant classes."""
    # Test Res1D class
    df = res1d_network.to_dataframe()
    assert isinstance(df, pd.DataFrame)
    
    # Test ResultLocation class (node)
    node = res1d_network.nodes["1"]
    df = node.to_dataframe()
    assert isinstance(df, pd.DataFrame)
    
    # Test ResultLocations class (nodes)
    df = res1d_network.nodes.to_dataframe()
    assert isinstance(df, pd.DataFrame)
    
    # Test ResultQuantityCollection class
    quantity_collection = res1d_network.nodes.quantities["WaterLevel"]
    df = quantity_collection.to_dataframe()
    assert isinstance(df, pd.DataFrame)
    
    # Test ResultQuantity class (base class for all quantities)
    quantity = res1d_network.nodes["1"].WaterLevel
    df = quantity.to_dataframe()
    assert isinstance(df, pd.DataFrame)
    
    # Test ResultQuantityDerived class if available
    if hasattr(res1d_network.nodes, "WaterLevelPlusOne"):
        derived_quantity = res1d_network.nodes.WaterLevelPlusOne
        df = derived_quantity.to_dataframe()
        assert isinstance(df, pd.DataFrame)
