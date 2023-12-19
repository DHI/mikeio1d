import pytest
from .testdata import testdata

from pandas.testing import assert_frame_equal

from mikeio1d import Res1D


def testdata_name():
    import dataclasses

    return list(dataclasses.asdict(testdata).keys())


@pytest.mark.parametrize("extension", [".res1d", ".res", ".resx", ".out"])
def test_mikeio1d_generates_expected_dataframe_for_filetype(extension):
    for name in testdata_name():
        path = getattr(testdata, name)
        if not path.endswith(extension):
            continue
        df = Res1D(path).read()
        df = df.loc[
            :, ~df.columns.duplicated()
        ]  # TODO: Remove this when column names are guaranteed unique
        df_expected = testdata.get_expected_dataframe(name)
        assert_frame_equal(df, df_expected)
