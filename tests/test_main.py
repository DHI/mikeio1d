import pytest

from .testdata import testdata

import mikeio1d


def test_open_res1d():
    """Test that the open function can open a res1d file."""
    res = mikeio1d.open("tests/testdata/network.res1d")
    assert isinstance(res, mikeio1d.Res1D)


def test_open_xns11():
    """Test that the open function can open a xns11 file."""
    xns = mikeio1d.open("tests/testdata/xsections.xns11")
    assert isinstance(xns, mikeio1d.Xns11)
