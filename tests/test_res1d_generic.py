import pytest

from mikeio1d import Res1D


def test_get_timeseries_id_to_read(res1d_catchments: Res1D):
    tsids = res1d_catchments._get_timeseries_ids_to_read(None)
    assert tsids == []

    tsids = res1d_catchments._get_timeseries_ids_to_read([])
    assert tsids == []

    query = res1d_catchments.catchments["100_16_16"].TotalRunOff.get_query()
    tsids = res1d_catchments._get_timeseries_ids_to_read([query])
    assert len(tsids) == 1
    assert tsids[0] == res1d_catchments.catchments["100_16_16"].TotalRunOff._timeseries_id

    tsids = res1d_catchments._get_timeseries_ids_to_read(query)
    assert len(tsids) == 1
