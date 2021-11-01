import os
import pytest
import numpy as np

from mikeio1d.custom_exceptions import NoDataForQuery, InvalidQuantity
from mikeio1d.res1d import Res1D, QueryDataCatchment
from mikeio1d.dotnet import to_numpy


@pytest.fixture
def test_file_path():
    test_folder_path = os.path.dirname(os.path.abspath(__file__))
    # File taken from TestSuite: RainfallRunoff\SWQ\DemoSWQ1BaseMixedRRAD.res1d
    return os.path.join(test_folder_path, "testdata", "Catchments.res1d")


@pytest.fixture(params=[True, False])
def test_file(test_file_path, request):
    return Res1D(test_file_path, request.param)


def test_read(test_file):
    df = test_file.read()
    assert len(df) == 108


def test_quantities(test_file):
    quantities = test_file.quantities
    assert len(quantities) == 5


@pytest.mark.parametrize("query,expected", [
    (QueryDataCatchment("TotalRunOff", "20_2_2"), True),
    (QueryDataCatchment("ZinkRR", "22_8_8"), True),
    (QueryDataCatchment("TotalRunOff", "wrong_catchment_name"), False)
])
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


@pytest.mark.parametrize("quantity,catchment_id,expected_max", [
    ("TotalRunoff", "20_2_2", 0.236),
    ("TotalRunoff", "22_8_8", 0.231)
])
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


def test_res1d_filter(test_file_path):
    catchments = ["20_2_2", "22_8_8"]
    res1d = Res1D(test_file_path, catchments=catchments)

    res1d.read(QueryDataCatchment("TotalRunOff", "20_2_2"))
    res1d.read(QueryDataCatchment("TotalRunOff", "22_8_8"))

    # Currently Mike1D raises NullReferenceException when requesting location not included by filter
    # This should be fixed in Mike1D to raise more meaningful Mike1DException
    # with pytest.raises(Exception):
    #     assert res1d.read(QueryDataCatchment("TotalRunOff", "100_16_16"))


def test_res1d_filter_readall(test_file_path):
    # Make sure readall works with filters
    catchments = ["20_2_2", "22_8_8"]
    res1d = Res1D(test_file_path, catchments=catchments)

    res1d.read()
