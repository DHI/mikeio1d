import os
import pytest
import numpy as np

from mikeio1d.custom_exceptions import NoDataForQuery, InvalidQuantity
from mikeio1d.res1d import Res1D
from mikeio1d.query import QueryDataCatchment
from mikeio1d.dotnet import to_numpy
from mikeio1d.result_reader_writer.result_reader import ColumnMode


@pytest.fixture
def test_file_path():
    test_folder_path = os.path.dirname(os.path.abspath(__file__))
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


@pytest.mark.parametrize(
    "query,expected",
    [
        (QueryDataCatchment("SWMM_SUBCATCH_RUNOFF", "5"), True),
        (QueryDataCatchment("SWMM_SUBCATCH_EVAP", "6"), True),
        (QueryDataCatchment("SWMM_SUBCATCH_RUNOFF", "wrong_catchment_name"), False),
    ],
)
def test_valid_catchment_data_queries(test_file, query, expected):
    swmm_out = test_file

    with pytest.raises(InvalidQuantity):
        invalid_query = QueryDataCatchment("InvalidQuantity", "20_2_2")
        assert swmm_out.read(invalid_query)

    if expected:
        swmm_out.read(query)
    else:
        with pytest.raises(NoDataForQuery):
            assert swmm_out.read(query)
        pass


@pytest.mark.parametrize(
    "query,expected_max",
    [
        (QueryDataCatchment("SWMM_SUBCATCH_RUNOFF", "5"), 6.562),
        (QueryDataCatchment("SWMM_SUBCATCH_RUNOFF", "6"), 1.495),
    ],
)
def test_read_reach_with_queries(test_file, query, expected_max):
    data = test_file.read(query)
    assert pytest.approx(round(data.max().values[0], 3)) == expected_max


@pytest.mark.parametrize(
    "quantity,catchment_id,expected_max",
    [("SWMM_SUBCATCH_RUNOFF", "5", 6.562), ("SWMM_SUBCATCH_RUNOFF", "6", 1.495)],
)
def test_read_catchment(test_file, quantity, catchment_id, expected_max):
    data = test_file.query.GetCatchmentValues(catchment_id, quantity)
    data = to_numpy(data)
    actual_max = round(np.max(data), 3)
    print(actual_max)
    assert pytest.approx(actual_max) == expected_max


def test_time_index(test_file):
    assert len(test_file.time_index) == 36


def test_start_time(test_file):
    assert test_file.start_time == test_file.time_index.min()


def test_get_catchment_values(test_file):
    values = test_file.get_catchment_values("5", "SWMM_SUBCATCH_RUNOFF")
    assert len(values) == 36


def test_dotnet_methods(test_file):
    swmm_out = test_file
    # Just try to access the properties and methods in .net
    swmm_out.data.ResultSpecs
    swmm_out.data.Catchments
    swmm_out.query.GetCatchmentValues("5", "SWMM_SUBCATCH_RUNOFF")


def test_swmm_out_filter(test_file_path, helpers):
    catchments = ["5", "6"]
    swmm_out = Res1D(test_file_path, catchments=catchments)
    swmm_out.result_reader.column_mode = ColumnMode.ALL

    df_5 = swmm_out.read(QueryDataCatchment("SWMM_SUBCATCH_RUNOFF", "5"))
    df_6 = swmm_out.read(QueryDataCatchment("SWMM_SUBCATCH_RUNOFF", "6"))

    swmm_out_full = Res1D(test_file_path)
    swmm_out_full.result_reader.column_mode = ColumnMode.ALL
    df_full = swmm_out_full.read()

    helpers.assert_shared_columns_equal(df_full, df_5)
    helpers.assert_shared_columns_equal(df_full, df_6)

    # Currently Mike1D raises NullReferenceException when requesting location not included by filter
    # This should be fixed in Mike1D to raise more meaningful Mike1DException
    # with pytest.raises(Exception):
    #     assert swmm_out.read(QueryDataCatchment("SWMM_SUBCATCH_RUNOFF", "10xyz"))


def test_swmm_out_filter_readall(test_file_path):
    # Make sure readall works with filters
    catchments = ["5", "6"]
    swmm_out = Res1D(test_file_path, catchments=catchments)

    # Does not work on MIKE 1D side, giving System.NullReferenceException
    # >>> swmm_out.read()
