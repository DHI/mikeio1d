"""MIKE IO 1D library for Python."""

from __future__ import annotations

import re
import sys
import warnings
import platform
from pathlib import Path
from typing import Tuple

from importlib.metadata import metadata

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
__version__ = "1.2.0"


def python_upper_boundary(py_req: str) -> Tuple[int, int]:
    """Fetch the upper boundary of mikeio1d of python defined in pyproject.toml.

    Returns
    -------
    Tuple[int, int]
        Python version as a tuple
    """
    # Regex to match decimals after <, <=, or =<
    # Explanation:
    # (?<=pattern) → positive lookbehind (asserts what comes before)
    # <|<=|=<    → matches <, <=, or =<
    # \d+\.\d+   → matches a decimal number (e.g., 3.45)
    pattern = r"(?:(?<=<)|(?<=<=)|(?<==<))\d+\.\d+"
    upper_boundary = re.findall(pattern, py_req)
    if len(upper_boundary) == 0:
        return sys.version_info
    elif len(upper_boundary) == 1:
        return tuple(int(v) for v in upper_boundary[0].split("."))
    else:
        raise ValueError(
            "'requires-python' field is not properly set: multiple upper boundaries were found."
        )


python_requirements = metadata("mikeio1d").get("Requires-Python")
max_python = python_upper_boundary(python_requirements)
python_version = (sys.version_info.major, sys.version_info.minor)
print(max_python, python_version)
if python_version > max_python:
    max_python_version = ".".join([str(n) for n in max_python])
    warnings.warn(
        f"'mikeio1d' officially supports Python <= {max_python_version} and you are using Python {sys.version_info.major}.{sys.version_info.minor}. "
        "Functionality may be unstable, likely due to incompatibilities with 'pythonnet'.",
        stacklevel=2,
    )

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
from .top_level import open

from .various import allow_nested_autocompletion_for_ipython

allow_nested_autocompletion_for_ipython(Res1D)
allow_nested_autocompletion_for_ipython(Xns11)


__all__ = ["Res1D", "Xns11", "open"]
