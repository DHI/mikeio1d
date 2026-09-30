import pytest
from pathlib import Path

import mikeio1d
from mikeio1d.res1d import Res1D
from mikeio1d.xns11 import Xns11


@pytest.mark.parametrize(
    "filename",
    [
        "tests/testdata/network.res1d",
        Path("tests/testdata/network.res1d"),
    ],
    ids=["str", "pathlib"],
)
def test_open_res1d(filename):
    """Test that the open function can open a res1d file."""
    res = mikeio1d.open(filename)
    assert isinstance(res, mikeio1d.Res1D)

    res = Res1D(filename)
    assert isinstance(res, mikeio1d.Res1D)


@pytest.mark.parametrize(
    "filename",
    [
        "tests/testdata/xsections.xns11",
        Path("tests/testdata/xsections.xns11"),
    ],
    ids=["str", "pathlib"],
)
def test_open_xns11(filename):
    """Test that the open function can open a xns11 file."""
    xns = mikeio1d.open(filename)
    assert isinstance(xns, mikeio1d.Xns11)

    xns = Xns11(filename)
    assert isinstance(xns, mikeio1d.Xns11)
