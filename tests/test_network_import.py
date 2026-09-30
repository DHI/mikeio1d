"""Test what importing the module says when its optional dependencies are absent.

The module needs networkx and xarray, which only the ``network`` extra installs,
so the first thing a user without the extra meets is an import error. It has to
name the extra: the module that happened to be imported first is no help.
"""

import subprocess
import sys
import textwrap

import pytest

_BLOCK_NETWORKX_AND_IMPORT = textwrap.dedent(
    """
    import sys
    from importlib.abc import MetaPathFinder


    class Block(MetaPathFinder):
        def find_spec(self, name, path=None, target=None):
            if name == "networkx":
                raise ImportError("blocked for the sake of the test")


    sys.meta_path.insert(0, Block())

    try:
        import mikeio1d.network
    except ImportError as err:
        print(err)
    """
)


@pytest.mark.slow
def test_a_missing_dependency_names_the_extra_to_install():
    """In a subprocess: the check runs at import, and this session has the extra.

    Marked slow because that subprocess loads the .NET assemblies from
    scratch, which costs seconds for the sake of one error message.
    """
    done = subprocess.run(
        [sys.executable, "-c", _BLOCK_NETWORKX_AND_IMPORT],
        capture_output=True,
        text=True,
    )

    assert done.returncode == 0, done.stderr
    assert "pip install mikeio1d[network]" in done.stdout
