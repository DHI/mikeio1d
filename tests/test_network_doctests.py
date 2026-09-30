"""Run the network module's docstring examples, and check every public member has one.

The examples open fixtures by their path from the repository root, as a reader
running them from a checkout would.
"""

# ruff: noqa: E402
import ast
import doctest
import importlib
import inspect
import itertools
import pkgutil
from pathlib import Path

import pytest

pytest.importorskip("networkx")

import mikeio1d.network

_ROOT = Path(__file__).parents[1]
_FLAGS = doctest.ELLIPSIS | doctest.NORMALIZE_WHITESPACE


def _modules():
    """The network package and every module in it."""
    names = [info.name for info in pkgutil.iter_modules(mikeio1d.network.__path__)]
    return [mikeio1d.network] + [
        importlib.import_module(f"mikeio1d.network.{name}") for name in names
    ]


def _address_docstring():
    """The docstring of the Address alias, which only the source holds.

    An alias has no ``__doc__`` of its own, so doctest cannot find the string
    literal after it, though quartodoc renders it.
    """
    module = mikeio1d.network._naming
    path = Path(module.__file__)
    body = ast.parse(path.read_text(encoding="utf-8")).body
    for statement, following in itertools.pairwise(body):
        targets = getattr(statement, "targets", [])
        if [getattr(target, "id", None) for target in targets] == ["Address"]:
            return following.value.value, path, following.lineno
    raise AssertionError("No docstring follows the Address alias.")


def _doctests():
    finder = doctest.DocTestFinder()
    found = [test for module in _modules() for test in finder.find(module) if test.examples]
    docstring, path, lineno = _address_docstring()
    found.append(
        doctest.DocTestParser().get_doctest(
            docstring,
            dict(vars(mikeio1d.network._naming)),
            "mikeio1d.network.Address",
            str(path),
            lineno,
        )
    )
    return found


def _public_members():
    """Every name the package exports, and each exported class's public members."""
    for name in mikeio1d.network.__all__:
        if name == "Address":
            continue
        exported = getattr(mikeio1d.network, name)
        yield name, exported
        for member_name, member in vars(exported).items():
            is_member = inspect.isfunction(member) or isinstance(
                member, (property, classmethod, staticmethod)
            )
            if is_member and not member_name.startswith("_"):
                yield f"{name}.{member_name}", member


@pytest.mark.parametrize("test", _doctests(), ids=lambda test: test.name)
def test_the_example_gives_what_it_shows(test, monkeypatch):
    monkeypatch.chdir(_ROOT)
    runner = doctest.DocTestRunner(optionflags=_FLAGS)

    runner.run(test)

    assert runner.summarize(verbose=False).failed == 0


@pytest.mark.parametrize("name, member", list(_public_members()), ids=lambda x: str(x))
def test_every_public_member_has_an_example(name, member):
    docstring = inspect.getdoc(member.__func__ if isinstance(member, classmethod) else member)

    assert docstring and ">>>" in docstring, f"{name} has no Examples"


def test_address_has_an_example():
    docstring, _, _ = _address_docstring()

    assert ">>>" in docstring
