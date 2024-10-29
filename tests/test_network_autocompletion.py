"""
The purpose of this test is to verify that the autocompletion of a network is working as expected.
"""

import pytest
from IPython.core.interactiveshell import InteractiveShell

from typing import List


@pytest.fixture(scope="module")
def shell():
    shell = InteractiveShell()
    shell.run_cell("""
    from mikeio1d.res1d import _allow_autocompletion_for_nested_network_in_ipython
    _allow_autocompletion_for_nested_network_in_ipython()            
    """)
    shell.run_cell(
        """
    from mikeio1d import Res1D
    from tests import testdata
    res = Res1D(testdata.network_river_res1d)
    """
    )
    return shell


def complete(shell, prompt) -> List[str]:
    prompt, completions = shell.complete(prompt)
    completions = [c[len(prompt) :] for c in completions]
    return completions


def test_reach_names(shell):
    completions = complete(shell, "res.reaches['")
    assert "river" in completions


def test_reach_chainages(shell):
    completions = complete(shell, "res.reaches['river']['")
    assert "53100.000" in completions
