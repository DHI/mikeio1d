"""Open a result file, and its companions, as what a network is built from.

:class:`~mikeio1d.network.Network` knows nothing of file formats: it is handed
reaches and the results to read through. Deciding whether a file can be a
network, which companions to read beside it, and how to say which one failed
all happen here.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Sequence
    from pathlib import Path

    from ..res1d import Res1D
    from ._results import _Results
    from ._types import NetworkReach

from ._companions import _companion_paths
from ._companions import _read_companions
from ._policy import _as_res1d
from ._policy import _path_of
from ._policy import _validate_extension
from ._res1d import _load_res1d_network


def _blame_the_companions(
    res: Res1D, found: Sequence[str | Path | Res1D], err: Exception
) -> ValueError:
    """Name the companions in an error about them, for a caller who asked for none.

    A companion found beside the result file has to be named when it turns out
    to be the problem, or the error points at files the caller did not know were
    being read.
    """
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

    found, discovered = _companion_paths(res, companions)
    # Every failure a companion can cause is raised while reading it, so a
    # fault in the result file itself keeps its own message.
    try:
        extra, lengths = _read_companions(res, found)
    except ValueError as err:
        if not discovered:
            raise
        raise _blame_the_companions(res, found, err) from err

    return _load_res1d_network(res, extra=extra, lengths=lengths)
