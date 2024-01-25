import os
import pytest
import numpy as np
import pandas as pd

from mikeio1d.custom_exceptions import NoDataForQuery, InvalidQuantity
from mikeio1d.res1d import Res1D
from mikeio1d.query import QueryDataCatchment
from mikeio1d.dotnet import to_numpy
from mikeio1d.result_network import ResultCatchment
from mikeio1d.result_reader_writer.result_reader import ColumnMode


@pytest.fixture
def test_file_path():
    test_folder_path = os.path.dirname(os.path.abspath(__file__))
    # File taken from TestSuite: RainfallRunoff\SWQ\DemoSWQ1BaseMixedRRAD.res1d
    return os.path.join(test_folder_path, "testdata", "catchments.res1d")


@pytest.fixture
def test_file_path_for_merging():
    test_folder_path = os.path.dirname(os.path.abspath(__file__))
    # File taken from TestSuite: RainfallRunoff\SWQ\DemoSWQ1BaseMixedRRAD.res1d
    return os.path.join(test_folder_path, "testdata", "catchment_merge.res1d")


@pytest.fixture(params=[True, False])
def test_file(test_file_path, request):
    return Res1D(test_file_path, lazy_load=request.param)


def test_read(test_file):
    df = test_file.read()
    assert len(df) == 108
    # TODO: assert not df.columns.duplicated().any() - add this, but it fails since columns are not guaranteed unique


def test_quantities(test_file):
    quantities = test_file.quantities
    assert len(quantities) == 5


def test_info(test_file):
    res1d = test_file
    res1d_info = res1d._get_info()
    res1d_info_ref = (
        "Start time: 1994-08-07 16:35:00\n"
        + "End time: 1994-08-07 18:35:00\n"
        + "# Timesteps: 108\n"
        + "# Catchments: 31\n"
        + "# Nodes: 0\n"
        + "# Reaches: 0\n"
        + "# Globals: 0\n"
        + "0 - TotalRunOff <m^3/s>\n"
        + "1 - ActualRainfall <m/s>\n"
        + "2 - ZinkLoadRR <kg/s>\n"
        + "3 - ZinkMassAccumulatedRR <kg>\n"
        + "4 - ZinkRR <mg/l>"
    )
    assert res1d_info == res1d_info_ref


def test_data_item_dicts(test_file):
    res1d = test_file
    assert len(res1d.catchments) == 31
    assert len(res1d.nodes) == 0
    assert len(res1d.reaches) == 0
    assert len(res1d.global_data) == 0


@pytest.mark.parametrize(
    "query,expected",
    [
        (QueryDataCatchment("TotalRunOff", "20_2_2"), True),
        (QueryDataCatchment("ZinkRR", "22_8_8"), True),
        (QueryDataCatchment("TotalRunOff", "wrong_catchment_name"), False),
    ],
)
def test_valid_catchment_data_queries(test_file, query, expected):
    res1d = test_file

    with pytest.raises(InvalidQuantity):
        invalid_query = QueryDataCatchment("InvalidQuantity", "20_2_2")
        assert res1d.read(invalid_query)

    if expected:
        res1d.read(query)
    else:
        with pytest.raises(NoDataForQuery):
            assert res1d.read(query)
        pass


@pytest.mark.parametrize(
    "query,expected_max",
    [
        (QueryDataCatchment("TotalRunOff", "20_2_2"), 0.236),
        (QueryDataCatchment("TotalRunOff", "22_8_8"), 0.231),
    ],
)
def test_read_catchment_with_queries(test_file, query, expected_max):
    data = test_file.read(query)
    assert pytest.approx(round(data.max().values[0], 3)) == expected_max


@pytest.mark.parametrize(
    "quantity,catchment_id,expected_max",
    [("TotalRunoff", "20_2_2", 0.236), ("TotalRunoff", "22_8_8", 0.231)],
)
def test_read_catchment(test_file, quantity, catchment_id, expected_max):
    data = test_file.query.GetCatchmentValues(catchment_id, quantity)
    data = to_numpy(data)
    actual_max = round(np.max(data), 3)
    print(actual_max)
    assert pytest.approx(actual_max) == expected_max


def test_time_index(test_file):
    assert len(test_file.time_index) == 108


def test_start_time(test_file):
    assert test_file.start_time == test_file.time_index.min()


def test_get_catchment_values(test_file):
    values = test_file.get_catchment_values("20_2_2", "TotalRunOff")
    assert len(values) == 108


def test_dotnet_methods(test_file):
    res1d = test_file
    # Just try to access the properties and methods in .net
    res1d.data.ResultSpecs
    res1d.data.Catchments
    res1d.query.GetCatchmentValues("20_2_2", "TotalRunOff")


def test_res1d_filter(test_file_path, helpers):
    catchments = ["20_2_2", "22_8_8"]
    res1d = Res1D(test_file_path, catchments=catchments)

    df_20_2_2 = res1d.read(QueryDataCatchment("TotalRunOff", "20_2_2"))
    df_22_8_8 = res1d.read(QueryDataCatchment("TotalRunOff", "22_8_8"))

    res1d_full = Res1D(test_file_path)
    df_full = res1d_full.read()

    helpers.assert_shared_columns_equal(df_full, df_20_2_2)
    helpers.assert_shared_columns_equal(df_full, df_22_8_8)

    # Currently Mike1D raises NullReferenceException when requesting location not included by filter
    # This should be fixed in Mike1D to raise more meaningful Mike1DException
    # with pytest.raises(Exception):
    #     assert res1d.read(QueryDataCatchment("TotalRunOff", "100_16_16"))


def test_res1d_filter_readall(test_file_path, helpers):
    # Make sure readall works with filters
    catchments = ["20_2_2", "22_8_8"]
    res1d = Res1D(test_file_path, catchments=catchments)
    df = res1d.read()

    res1d_full = Res1D(test_file_path)
    df_full = res1d_full.read()

    helpers.assert_shared_columns_equal(df_full, df)


def test_catchment_attributes(test_file):
    res1d = test_file
    catchments = res1d.catchments

    catchments.c_20_2_2.TotalRunOff.add()
    catchments.c_22_8_8.TotalRunOff.add()
    df = res1d.read()

    column_mode = res1d.result_reader.column_mode
    if column_mode in (ColumnMode.ALL, ColumnMode.COMPACT):
        actual_max = round(df.T.query("quantity=='TotalRunOff' and name=='20_2_2'").T.max(), 3)
    elif column_mode == ColumnMode.STRING:
        actual_max = round(df["TotalRunOff:20_2_2"].max(), 3)
    assert pytest.approx(actual_max) == 0.236

    if column_mode in (ColumnMode.ALL, ColumnMode.COMPACT):
        actual_max = round(df.T.query("quantity=='TotalRunOff' and name=='22_8_8'").T.max(), 3)
    elif column_mode == ColumnMode.STRING:
        actual_max = round(df["TotalRunOff:22_8_8"].max(), 3)
    assert pytest.approx(actual_max) == 0.231


def test_all_catchments_attributes(test_file):
    res1d = test_file
    res1d.catchments.TotalRunOff.add()
    df = res1d.read()

    assert len(df.columns) == 31

    max_runoff = round(df.max().max(), 3)
    assert pytest.approx(max_runoff) == 0.469


def test_catchment_attribute_access_maintains_backwards_compat(res1d_catchments):
    res = res1d_catchments
    catchment = res.result_network.catchments["100_16_16"]
    with pytest.warns(UserWarning):
        assert catchment.Id == "100_16_16"
        assert pytest.approx(catchment.Area) == 22800.0
    for name, catchment in res.result_network.catchments.items():
        assert catchment.CatchmentName == name


def test_catchments_map_to_python_catchment(res1d_catchments):
    res = res1d_catchments
    catchment = res.result_network.catchments["100_16_16"]
    assert isinstance(catchment, ResultCatchment)


def test_catchment_static_attributes(res1d_catchments):
    res = res1d_catchments
    catchment = res.result_network.catchments["100_16_16"]
    assert catchment.id == "100_16_16"
    assert pytest.approx(catchment.area) == 22800.0
    assert catchment.type == "Kinematic Wave"
    # check that static attributes are accessible for all catchments
    for catchment in res.result_network.catchments.values():
        catchment.id
        catchment.area
        catchment.type


def test_res1d_merging(test_file_path_for_merging):
    file_a = test_file_path_for_merging.replace(".res1d", "_a.res1d")
    file_b = test_file_path_for_merging.replace(".res1d", "_b.res1d")
    file_c = test_file_path_for_merging.replace(".res1d", "_c.res1d")

    res1d_a = Res1D(file_a)
    res1d_b = Res1D(file_b)
    Res1D.merge([res1d_a, res1d_b], file_c)

    df_a = res1d_a.read()
    df_b = res1d_b.read().tail(-1)
    df_c = Res1D(file_c).read()

    df_merged = pd.concat([df_a, df_b])
    pd.testing.assert_frame_equal(df_merged, df_c)
