"""MIKE IO 1D library for Python."""

from __future__ import annotations

import sys
import platform
from pathlib import Path

from .mikepath import MikePath

# PEP0440 compatible formatted version, see:
# https://www.python.org/dev/peps/pep-0440/
#
# Generic release markers:
#   X.Y
#   X.Y.Z   # For bugfix releases
#
# Admissible pre-release markers:
#   X.YaN   # Alpha release
#   X.YbN   # Beta release
#   X.YrcN  # Release Candidate
#   X.Y     # Final release
#
# Dev branch marker is: 'X.Y.dev' or 'X.Y.devN' where N is an integer.
# 'X.Y.dev0' is the canonical version of 'X.Y.dev'
#
__version__ = "0.9.1"

if "64" not in platform.architecture()[0]:
    raise Exception("This library has not been tested for a 32 bit system.")

MikePath.setup_mike_installation(sys.path)

import clr

clr.AddReference("System")
clr.AddReference("System.Runtime")
clr.AddReference("System.Runtime.InteropServices")
clr.AddReference("DHI.Generic.MikeZero.DFS")
clr.AddReference("DHI.Generic.MikeZero.EUM")
# clr.AddReference('DHI.PFS')
# clr.AddReference('DHI.Projections')
clr.AddReference("DHI.Mike1D.Generic")
clr.AddReference("DHI.Mike1D.ResultDataAccess")
clr.AddReference("DHI.Mike1D.CrossSectionModule")
clr.AddReference("DHI.Mike1D.MikeIO")

from .res1d import Res1D
from .xns11 import Xns11

from .various import allow_nested_autocompletion_for_ipython

allow_nested_autocompletion_for_ipython(Res1D)
allow_nested_autocompletion_for_ipython(Xns11)

from .various import open as open_impl


def open(file_name: str | Path, **kwargs) -> Res1D | Xns11:
    """Open a file type supported by MIKE IO 1D file.

    Parameters
    ----------
    file_name : str or Path
        Path to the file to read.
    **kwargs
        Additional keyword arguments to pass to the relevant constructor.

    See Also
    --------
    mikeio1d.Res1D
    mikeio1d.Xns11

    Returns
    -------
    Res1D or Xns11
        The object representing the 1D file.

    Examples
    --------
    >>> import mikeio1d
    >>> res = mikeio1d.open("results.res1d")
    >>> res.nodes.read()

    >>> xs = mikeio1d.open("cross_section.xns11")
    >>> xs
    """
    return open_impl(file_name, **kwargs)


__all__ = ["Res1D", "Xns11"]
