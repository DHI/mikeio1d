import pytest

from pathlib import Path

from mikeio1d.xns11 import Xns11


@pytest.fixture
def file():
    return "tests/testdata/xsections.xns11"


def test_read(file):
    xns = Xns11(file)
    assert xns.file_path == Path(file)
    assert len(xns) == 61


@pytest.mark.parametrize(
    "topo_id, location_id, chainage,expected_bottom",
    [
        ("topoid1", "reach1", 58.68, 1626.16),
        ("topoid2", "reach2", -50, 1611.42),
        ("topoid1", "reach3", 11150.42, 1616.038),
        ("topoid1", "reach4", 13645.41, 1594.923),
    ],
)
def test_read_single_query_as_list(file, topo_id, location_id, chainage, expected_bottom):
    xns = Xns11(file)
    xs = xns.sel(location_id=location_id, chainage=chainage, topo_id=topo_id)
    bottom = xs.bottom_level
    assert pytest.approx(bottom) == expected_bottom
