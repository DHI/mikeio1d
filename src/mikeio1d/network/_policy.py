"""Which result formats a network can be built from, and which cannot yet.

``Res1D`` reads more formats than a network can be mapped onto, and the
difference is not a matter of taste: a ``.out`` keeps its connectivity in a
companion input file nobody parses yet, a ``.resx`` describes a network defined
in its sibling ``.res``, and the rest have no fixture here to verify against.
"""

from __future__ import annotations

from pathlib import Path

from ..res1d import Res1D

_NETWORK_EXTENSIONS = frozenset({".res1d", ".res11", ".res"})
"""Result files a network can be built from: MIKE 1D, MIKE 11 and EPANET."""

_NO_FIXTURE = (
    "{product} results are not supported yet: there is no test fixture for this "
    "format, so support cannot be verified. Please open an issue if you need it."
)
# A result file that holds timeseries but no topology of its own. The connectivity
# is in a companion file we do not parse yet.
_TOPOLOGY_IN_COMPANION_FILE = (
    "SWMM '.out' files carry no reach connectivity of their own - it lives in the "
    "companion '.inp' input file, which is not read as topology yet. Tracked in "
    "https://github.com/DHI/mikeio1d/issues/213."
)
# A companion result file: readable, but it describes a network defined elsewhere.
_COMPANION_RESULT_FILE = (
    "'.resx' holds extra EPANET results (tank volume, pump energy) for a network "
    "defined in the sibling '.res' file, so it has no topology of its own. Read the "
    "'.res' file and pass this one alongside it: "
    "Network.open(res, companions=[resx])."
)

_NO_NAME_FILTER_EXTENSIONS = frozenset({".resx"})
"""Result files whose series cannot be picked out by node or reach name.

A '.resx' opened with a node filter reads that node's series as zeros, without
an error. Its series can still be picked out by quantity.
"""

# extension -> why no network can be built from it, though Res1D reads it
_UNSUPPORTED_EXTENSIONS: dict[str, str] = {
    ".out": _TOPOLOGY_IN_COMPANION_FILE,
    ".resx": _COMPANION_RESULT_FILE,
    ".prf": _NO_FIXTURE.format(product="MOUSE"),
    ".crf": _NO_FIXTURE.format(product="MOUSE"),
    ".xrf": _NO_FIXTURE.format(product="MOUSE"),
    ".whr": _NO_FIXTURE.format(product="Water Hammer"),
}


def _validate_extension(suffix: str) -> None:
    """Check that a network can be built from a file with this extension."""
    extension = suffix.lower()

    # Checked before the supported set below, since these all *are* readable by
    # Res1D - it is the mapping onto a network that is missing.
    reason = _UNSUPPORTED_EXTENSIONS.get(extension)
    if reason is not None:
        raise NotImplementedError(f"Cannot build a network from '{suffix}' files. {reason}")

    supported = Res1D.get_supported_file_extensions()
    if extension not in supported:
        readable = sorted(supported - set(_UNSUPPORTED_EXTENSIONS))
        raise NotImplementedError(
            f"Unsupported file extension '{suffix}'. Supported extensions are {readable}."
        )

    # Reached only by a format Res1D has gained since the tables above were
    # written, which is why the tests check them against Res1D's own list.
    if extension not in _NETWORK_EXTENSIONS:
        raise NotImplementedError(
            f"File extension '{suffix}' is readable by Res1D but has no network mapping "
            "yet. Please open an issue if you need it."
        )


def _path_of(file: str | Path | Res1D) -> Path:
    """Give the path of a result file, whether named or already open."""
    if isinstance(file, Res1D):
        return Path(str(file.file_path))
    if isinstance(file, (str, Path)):
        return Path(file)
    raise TypeError(f"Expected a str, Path or Res1D object, got {type(file).__name__!r}")


def _suffix_of(file: str | Path | Res1D) -> str:
    """Give a result file's lower-case extension, including its dot."""
    return _path_of(file).suffix.lower()


def _as_res1d(file: str | Path | Res1D) -> Res1D:
    """Open a result file, or take one already open."""
    return file if isinstance(file, Res1D) else Res1D(str(_path_of(file)))
