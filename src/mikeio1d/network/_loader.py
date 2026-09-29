"""Open a result file, and its companions, as what a network is built from.

:class:`~mikeio1d.network.Network` knows nothing of file formats: it is handed
reaches and the results to read through. Deciding whether a file can be a
network, which companions to read beside it, and how to say which one failed
all happen here.

``Res1D`` reads more formats than a network can be mapped onto, and the
difference is not a matter of taste: a ``.out`` needs its sibling input file
for connectivity and still reports no reach lengths, a ``.resx`` describes a network defined
in its sibling ``.res``, and the rest have no fixture here to verify against.
"""

from __future__ import annotations

import warnings
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Sequence

    from ._results import _Results
    from ._types import NetworkReach

from ..res1d import Res1D
from ._companions import _companion_paths
from ._companions import _merge_companion
from ._companions import _read_companions
from ._res1d import _as_res1d
from ._res1d import _path_of
from ._res1d import _load_res1d_network
from ._res1d import _series_by_key_within
from ._res1d import _unfiltered
from ._res1d import _units_of

_NETWORK_EXTENSIONS = frozenset({".res1d", ".res11", ".res"})
"""Result files a network can be built from: MIKE 1D, MIKE 11 and EPANET."""

_NO_FIXTURE = (
    "{product} results are not supported yet: there is no test fixture for this "
    "format, so support cannot be verified. Please open an issue if you need it."
)
# A result file that holds timeseries but no topology of its own. MIKE 1D reads
# the connectivity from the sibling '.inp' when there is one, but a reach length
# from neither file.
_TOPOLOGY_IN_COMPANION_FILE = (
    "SWMM '.out' files carry no reach connectivity of their own - it lives in the "
    "sibling '.inp' input file - and no reach lengths are read for them. Tracked in "
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


def _refuse_or_warn_catchments(res: Res1D) -> None:
    """Refuse a file of catchments alone, and warn about catchments beside a network.

    A catchment is tied to no node or reach a network has, so it has no address.
    A file of catchments alone would open as an empty network, which looks like
    a network with nothing in it rather than one that could not be built.

    Raises
    ------
    NotImplementedError
        If the file holds catchments and no reaches.
    """
    catchments = res.catchments
    if not catchments:
        return

    name = Path(str(res.file_path)).name
    if not res.reaches:
        raise NotImplementedError(
            f"'{name}' holds {len(catchments)} catchment(s) and no reaches: catchments "
            "are not part of a network yet."
        )

    quantities = sorted({q for catchment in catchments.values() for q in catchment.quantities})
    warnings.warn(
        f"'{name}' holds {len(catchments)} catchment(s), which are not part of a network "
        f"yet, so the network leaves them and their quantities out: {quantities}.",
        stacklevel=4,
    )


def _blame_the_companions(
    res: Res1D, found: Sequence[str | Path | Res1D], err: Exception
) -> ValueError:
    """Name the companions in an error about them, for a caller who asked for none."""
    names = ", ".join(f"'{_path_of(companion).name}'" for companion in found)
    return ValueError(
        f"Failed to build a network from '{_path_of(res).name}': {err}\n"
        f"Companion files read alongside it, because they share its folder: "
        f"{names}. Pass companions=[] to read the result file on its own, or "
        "name the companions you want."
    )


def _load_network(
    res: str | Path | Res1D,
    companions: Sequence[str | Path | Res1D] | None,
) -> tuple[list[NetworkReach], _Results]:
    """Read a result file's topology, and the results a network reads through.

    Parameters
    ----------
    res : str, Path or Res1D
        The result file, or one already opened.
    companions : sequence of str, Path or Res1D, or None
        As :meth:`~mikeio1d.network.Network.open` takes them.

    Returns
    -------
    tuple of (list of NetworkReach, _Results)
        What :class:`~mikeio1d.network.Network` is constructed from.
    """
    # Before opening, so a file no network can come from is refused unread.
    _validate_extension(_path_of(res).suffix)
    res = _as_res1d(res)
    # A filtered Res1D decides which series are read, not what the network is.
    topology = _unfiltered(res)
    _refuse_or_warn_catchments(topology)

    series_by_key = _series_by_key_within(topology, res)
    units = _units_of(res)

    found, discovered = _companion_paths(res, companions)
    try:
        extra = _read_companions(topology, found)
        if extra is not None:
            series_by_key, units = _merge_companion(series_by_key, units, extra)
    except ValueError as err:
        if not discovered:
            raise
        raise _blame_the_companions(res, found, err) from err

    return _load_res1d_network(topology, series_by_key=series_by_key, units=units)
