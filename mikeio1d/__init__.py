"""MIKE IO 1D library for Python."""

from __future__ import annotations

import re
import sys
import warnings
import platform
from pathlib import Path
from packaging.specifiers import SpecifierSet

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

current_python_version = ".".join(map(str, sys.version_info[:3]))


def get_version_upper_boundary() -> str:
    """Fetch the python upper boundary of the 'requires-python' field in pyproject.toml.

    It works with strings like '>=3.13,<3.14'. Python upper boundary must not include the patch level.

    Returns
    -------
    str
        Upper boundary as specified in 'requires-python'
    """
    #     # Regex pattern explanation:
    #     # <=|=<|<    → Match one of the three operators: <=, =<, or <.
    #     #               The order matters: <= and =< are checked first so that
    #     #               the single < doesn't match inside them.
    #     # \s*          → Match zero or more spaces between the operator and the number.
    #     # \d+\.\d+   → Match a decimal number: one or more digits, a dot, then one or more digits.
    pattern = r"<=|=<|<\s*\d+\.\d+"
    requires_python = metadata("mikeio1d").get("Requires-Python")
    upper_boundary = re.findall(pattern, requires_python)
    if len(upper_boundary) == 0:
        return current_python_version
    elif len(upper_boundary) == 1:
        py_version = upper_boundary[0]
        return py_version
    else:
        raise RuntimeError("'requires-python' contains multiple upper boundaries.")


valid_python = get_version_upper_boundary()
if current_python_version not in SpecifierSet(valid_python):
    warnings.warn(
        f"'mikeio1d' officially supports Python {valid_python} and you are using Python {current_python_version}. "
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
