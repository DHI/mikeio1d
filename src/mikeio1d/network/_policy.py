"""Which result formats a network can be built from, and which cannot yet.

``Res1D`` reads more formats than a network can be mapped onto. The difference is
not a matter of taste: a ``.out`` keeps its connectivity in a companion input
file nobody parses yet, a ``.resx`` describes a network defined in its sibling
``.res``, and the rest have no fixture here to verify against.
"""

from __future__ import annotations

from ..res1d import Res1D

_MIKE_EXTENSIONS = frozenset({".res1d", ".res11"})
_EPANET_EXTENSIONS = frozenset({".res"})

_NO_FIXTURE = (
    "{product} results are not supported yet: modelskill has no test fixture for "
    "this format, so support cannot be verified. Please open an issue if you need it."
)
# A result file that holds timeseries but no topology of its own. The connectivity
# is in a companion file we do not parse yet.
_TOPOLOGY_IN_COMPANION_FILE = (
    "SWMM '.out' files carry no reach connectivity of their own - it lives in the "
    "companion '.inp' input file, which modelskill does not read yet. Tracked in "
    "https://github.com/DHI/modelskill/issues/689."
)
# A companion result file: readable, but it describes a network defined elsewhere.
_COMPANION_RESULT_FILE = (
    "'.resx' holds extra EPANET results (tank volume, pump energy) for a network "
    "defined in the sibling '.res' file, so it has no topology of its own. Read the "
    "'.res' file and pass this one alongside it: "
    "Network.from_epanet(res, resx=...)."
)

# extension -> why modelskill will not read it, even though mikeio1d can
_UNSUPPORTED_EXTENSIONS: dict[str, str] = {
    ".out": _TOPOLOGY_IN_COMPANION_FILE,
    ".resx": _COMPANION_RESULT_FILE,
    ".prf": _NO_FIXTURE.format(product="MOUSE"),
    ".crf": _NO_FIXTURE.format(product="MOUSE"),
    ".xrf": _NO_FIXTURE.format(product="MOUSE"),
    ".whr": _NO_FIXTURE.format(product="Water Hammer"),
}

# extension -> the constructor that reads it, for "use X instead" errors
_EXTENSION_CONSTRUCTORS: dict[str, str] = {
    **{extension: "from_mike" for extension in _MIKE_EXTENSIONS},
    **{extension: "from_epanet" for extension in _EPANET_EXTENSIONS},
}


def _validate_extension(suffix: str, *, allowed: frozenset[str], caller: str) -> None:
    """Check a file extension against mikeio1d and against one constructor.

    Raises
    ------
    NotImplementedError
        If modelskill cannot read the extension, either because mikeio1d
        does not support it or because modelskill does not.
    ValueError
        If another constructor is the one that reads this extension.
    """
    extension = suffix.lower()

    # Checked before the supported set below, since these all *are* readable
    # by mikeio1d - it is modelskill that cannot use the result.
    reason = _UNSUPPORTED_EXTENSIONS.get(extension)
    if reason is not None:
        raise NotImplementedError(f"Cannot read '{suffix}' files. {reason}")

    supported = Res1D.get_supported_file_extensions()
    if extension not in supported:
        readable = sorted(supported - set(_UNSUPPORTED_EXTENSIONS))
        raise NotImplementedError(
            f"Unsupported file extension '{suffix}'. Supported extensions are {readable}."
        )

    if extension not in allowed:
        constructor = _EXTENSION_CONSTRUCTORS.get(extension)
        if constructor is None:
            raise NotImplementedError(
                f"File extension '{suffix}' is supported by mikeio1d but is not mapped "
                "to a Network constructor in this version of modelskill. "
                "Please upgrade modelskill or open an issue."
            )
        raise ValueError(
            f"Network.{caller}() reads {sorted(allowed)} files, got '{suffix}'. "
            f"Use Network.{constructor}() instead."
        )
