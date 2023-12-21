import dataclasses
from dataclasses import dataclass
from pathlib import Path


def format_path(filename):
    path = Path(__file__).parent / filename
    return str(path.absolute())


# Using dataclass worked better for autocompletion in vscode
@dataclass
class testdata:
    """
    A class that contains file paths for test data used in the mikeio1d package.
    Useful for testing and examples, without having to get path. Works for unsaved
    notebooks as well.

    Examples
    --------
    >>> from mikeio1d import Res1D
    >>> from tests import testdata
    >>> res = Res1D(testdata.network_res1d)
    """

    network_res1d: str = format_path("network.res1d")
    """A basic urban network file."""
    network_res1d_chinese: str = format_path("network_chinese.res1d")
    """A basic urban network file with chinese characters for some links."""
    network_river_res1d: str = format_path("network_river.res1d")
    """A basic river network file."""
    catchments_res1d: str = format_path("catchments.res1d")
    """A small urban setup with three pipes."""
    flow_split_res1d: str = format_path("flow_split.res1d")
    """A basic urban network file containing only catchments."""
    lts_event_statistics_res1d: str = format_path("lts_event_statistics.res1d")
    """An LTS event statistics file."""
    lts_monthly_statistics_res1d: str = format_path("lts_monthly_statistics.res1d")
    """An LTS monthly statistics file."""
    xsections_xns11: str = format_path("xsections.xns11")
    """A basic xsections file."""
    epanet_res: str = format_path("epanet.res")
    """A basic Epanet res file. Must have accompanying .inp file."""
    epanet_resx: str = format_path("epanet.resx")
    """A basic Epanet resx file. Must have accompanying .inp file."""
    swmm_out: str = format_path("swmm.out")
    """A basic SWMM result file. Must have accompanying .inp file."""

    def get_expected_dataframe(self, name: str):
        import pandas as pd

        return pd.read_parquet(Path(__file__).parent / "expected_results" / f"{name}.parquet")


testdata = testdata()


def generate_expected_results(output_folder: Path = Path(__file__).parent / "expected_results"):
    import pandas as pd
    from pandas.testing import assert_frame_equal
    from mikeio1d import Res1D

    if not output_folder.exists():
        output_folder.mkdir()
    for name, path in dataclasses.asdict(testdata).items():
        if path.endswith(".xns11"):
            continue
        res = Res1D(path)
        df = res.read()
        df = df.loc[
            :, ~df.columns.duplicated()
        ]  # TODO: Remove this when column names are guaranteed unique
        output_path = output_folder / f"{name}.parquet"
        df.to_parquet(output_path)
        df_parquet = testdata.get_expected_dataframe(name)
        assert_frame_equal(df, df_parquet)
