import pytest
from .testdata import testdata

from typing import List
import random

from pandas.testing import assert_frame_equal

from mikeio1d import Res1D
from mikeio1d.quantities import TimeSeriesId
from mikeio1d.query import QueryData

from mikeio1d.result_reader_writer.result_reader import ColumnMode


def testdata_name():
    import dataclasses

    return list(dataclasses.asdict(testdata).keys())


@pytest.mark.slow
@pytest.mark.parametrize("extension", [".res1d", ".res", ".resx", ".out"])
@pytest.mark.parametrize("result_reader", ["copier", "query"])
def test_mikeio1d_generates_expected_dataframe_for_filetype_read_all(result_reader, extension):
    for name in testdata_name():
        path = getattr(testdata, name)
        if not path.endswith(extension):
            continue
        column_mode = ColumnMode.STRING if result_reader == "copier" else None
        df = Res1D(path, result_reader_type=result_reader).read(column_mode=column_mode)
        df = df.loc[
            :, ~df.columns.duplicated()
        ]  # TODO: Remove this when column names are guaranteed unique
        df_expected = testdata.get_expected_dataframe(name)
        assert_frame_equal(df, df_expected)


def sample_random_time_series_ids(res: Res1D) -> List[TimeSeriesId]:
    all_tsids = list(res.result_network.result_quantity_map.keys())
    sample_tsids = [t for t in all_tsids if random.random() < 0.5]
    return sample_tsids


def sample_random_queries(res: Res1D) -> List[str]:
    all_tsids = list(res.result_network.result_quantity_map.values())
    all_queries = [t.get_query() for t in all_tsids]
    sample_queries = [q for q in all_queries if random.random() < 0.5]
    return sample_queries


@pytest.mark.slow
@pytest.mark.parametrize("extension", [".res1d", ".res", ".resx", ".out"])
@pytest.mark.parametrize("result_reader", ["copier", "query"])
def test_mikeio1d_generates_dataframe_reading_time_series_ids(result_reader, extension):
    for name in testdata_name():
        path = getattr(testdata, name)
        if not path.endswith(extension):
            continue
        res = Res1D(path, result_reader_type=result_reader)
        sample_tsids = sample_random_time_series_ids(res)
        df = res.read(sample_tsids)
        assert len(df) > 0


@pytest.mark.slow
@pytest.mark.parametrize("extension", [".res1d", ".res", ".resx", ".out"])
@pytest.mark.parametrize("result_reader", ["copier", "query"])
def test_mikeio1d_generates_dataframe_reading_queries(result_reader, extension):
    for name in testdata_name():
        path = getattr(testdata, name)
        if not path.endswith(extension):
            continue
        res = Res1D(path, result_reader_type=result_reader)
        sample_queries = sample_random_queries(res)
        df = res.read(sample_queries)
        assert len(df) > 0


@pytest.mark.slow
@pytest.mark.parametrize("extension", [".res1d", ".res", ".resx", ".out"])
@pytest.mark.parametrize(
    "column_mode", [ColumnMode.ALL, ColumnMode.COMPACT, ColumnMode.TIMESERIES, ColumnMode.STRING]
)
def test_mikeio1d_all_column_modes_basic(extension, column_mode):
    """Basic check that no errors are raised for reading in all column modes."""
    for name in testdata_name():
        path = getattr(testdata, name)
        if not path.endswith(extension):
            continue
        res = Res1D(path)
        sample_queries = sample_random_queries(res)
        df = res.read(sample_queries, column_mode=column_mode)
        assert len(df) > 0
        df = res.read(column_mode=column_mode)
        assert len(df) > 0
