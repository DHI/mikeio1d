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
    >>> res = Res1D(testdata.Network_res1d)
    """

    Network_res1d: str = format_path("Network.res1d")
    """A basic urban network file."""
    Network_res1d_chinese: str = format_path("Network_chinese.res1d")
    """A basic urban network file with chinese characters for some links."""
    NetworkRiver_res1d: str = format_path("NetworkRiver.res1d")
    """A basic river network file."""
    Catchments_res1d: str = format_path("Catchments.res1d")
    """A small urban setup with three pipes."""
    FlowSplit_res1d: str = format_path("FlowSplit.res1d")
    """A basic urban network file containing only catchments."""
    LTSEventStatistics_res1d: str = format_path("LTSEventStatistics.res1d")
    """An LTS event statistics file."""
    LTSMonthlyStatistics_res1d: str = format_path("LTSMonthlyStatistics.res1d")
    """An LTS monthly statistics file."""
    xsections_xns11: str = format_path("xsections.xns11")
    """A basic xsections file."""
    Epanet_res: str = format_path("Epanet.res")
    """A basic Epanet res file. Must have accompanying .inp file."""
    Epanet_resx: str = format_path("Epanet.resx")
    """A basic Epanet resx file. Must have accompanying .inp file."""
    SWMM_out: str = format_path("SWMM.out")
    """A basic SWMM result file. Must have accompanying .inp file."""


testdata = testdata()
