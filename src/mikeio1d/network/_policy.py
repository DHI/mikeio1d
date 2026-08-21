"""Which result formats a network can be built from, and which cannot yet.

``Res1D`` reads more formats than a network can be mapped onto, and the
difference is not a matter of taste: a ``.out`` keeps its connectivity in a
companion input file nobody parses yet, a ``.resx`` describes a network defined
in its sibling ``.res``, and the rest have no fixture here to verify against.
"""

from __future__ import annotations

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
    """Check that a network can be built from a file with this extension.

    Parameters
    ----------
    suffix : str
        The file extension, including its dot.

    Raises
    ------
    NotImplementedError
        If ``Res1D`` cannot read the extension at all, if it can read it but the
        result holds no network to map, or if it is a format nothing has mapped
        onto a network yet.
    """
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
