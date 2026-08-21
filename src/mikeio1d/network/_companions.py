"""Files read alongside a result file, and the names they use.

An EPANET run writes up to three files worth reading: the ``.res`` holding the
network and its main results, a ``.resx`` holding extra results for the same
network, and the ``.inp`` input file, which is the only one carrying reach
lengths. A companion is found by sharing the result file's folder and stem.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ..res1d import Res1D
from ._inp import read_pipe_lengths

_COMPANION_SEARCH_EXTENSIONS = frozenset({".res"})
"""Result extensions whose companions can be found by folder and stem."""

# The encodings a companion file's text is worth re-reading as. mikeio1d hands
# back '.res' names decoded as UTF-8 but '.resx' names decoded with the Windows
# ANSI codepage, so a name holding a non-ASCII character arrives spelled two
# ways from one model. cp1252 is that codepage on a Western-European Windows.
_COMPANION_ENCODINGS = ("cp1252", "latin-1")


def _repair_mis_decoded(name: str) -> list[str]:
    """Re-read a name as UTF-8, undoing a single-byte decoding of those bytes.

    Parameters
    ----------
    name : str
        A location name as the companion file reported it.

    Returns
    -------
    list of str
        The candidate spellings, which is empty when no encoding round-trips.
        A caller must check a candidate against the main file before using it:
        the encoding that produced the name is a guess.
    """
    candidates = []
    for encoding in _COMPANION_ENCODINGS:
        try:
            repaired = name.encode(encoding).decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            continue
        if repaired != name and repaired not in candidates:
            candidates.append(repaired)
    return candidates


def _rekey_by_main_file(locations: Any, known: Any) -> dict[str, Any]:
    """Key a companion file's locations by their names in the main result file.

    A name that already matches, or that no re-reading reconciles, keeps the
    spelling it came with — so a companion from a genuinely different model
    still holds names the main file does not, and validation still catches it.

    Parameters
    ----------
    locations : mapping of str to location
        The companion file's nodes or reaches.
    known : container of str
        The main file's names for the same kind of location.

    Returns
    -------
    dict of str to location
    """
    rekeyed = {}
    for name in locations:
        key = name
        if name not in known:
            key = next(
                (c for c in _repair_mis_decoded(name) if c in known),
                name,
            )
        rekeyed[key] = locations[name]
    return rekeyed


class _Companion:
    """A companion result file, keyed by the main file's location names.

    Stands in for the ``Res1D`` it wraps everywhere the loader reaches into a
    companion, so a node or reach is found under one spelling of its name.
    """

    def __init__(self, res: Res1D, extra: Res1D) -> None:
        self.nodes = _rekey_by_main_file(extra.nodes, res.nodes)
        self.reaches = _rekey_by_main_file(extra.reaches, res.reaches)


def _read_companion_lengths(inp: str | Path) -> dict[str, float]:
    """Read reach lengths from a companion ``.inp`` input file."""
    path = Path(inp)
    if path.suffix.lower() != ".inp":
        raise ValueError(
            f"Expected an EPANET '.inp' input file, got '{path.suffix}'. "
            "This argument reads reach lengths from the model input, not "
            "from a result file."
        )
    return read_pipe_lengths(path)


def _open_companion_result(res: Res1D, resx: str | Path | Res1D) -> _Companion:
    """Open and validate a companion ``.resx`` result file.

    Returns
    -------
    _Companion
        The companion's locations, keyed by their names in ``res``.

    Raises
    ------
    ValueError
        If the extension is not ``.resx``, or if the file does not come from
        the same run as ``res``.
    """
    if isinstance(resx, (str, Path)):
        path = Path(resx)
        if path.suffix.lower() != ".resx":
            raise ValueError(f"Expected an EPANET '.resx' companion file, got '{path.suffix}'.")
        extra = Res1D(str(path))
    elif isinstance(resx, Res1D):
        if Path(resx.file_path).suffix.lower() != ".resx":
            raise ValueError(
                f"Expected an EPANET '.resx' companion file, got '{Path(resx.file_path).suffix}'."
            )
        extra = resx
    else:
        raise TypeError(f"Expected a str, Path or Res1D object, got {type(resx).__name__!r}")

    # Merging two different runs would line up silently and produce a network
    # that is wrong in a way no later error would reveal.
    if not res.time_index.equals(extra.time_index):
        raise ValueError(
            "The '.resx' companion does not share a time axis with the "
            "'.res' file, so the two are not from the same run. Got "
            f"{len(extra.time_index)} steps ending {extra.end_time} against "
            f"{len(res.time_index)} ending {res.end_time}."
        )

    companion = _Companion(res, extra)

    unknown_nodes = set(companion.nodes) - set(res.nodes)
    if unknown_nodes:
        raise ValueError(
            f"The '.resx' companion holds nodes {sorted(unknown_nodes)} that are "
            "absent from the '.res' network, so the two files do not describe "
            "the same model."
        )

    unknown_reaches = set(companion.reaches) - set(res.reaches)
    if unknown_reaches:
        raise ValueError(
            f"The '.resx' companion holds reaches {sorted(unknown_reaches)} that are "
            "absent from the '.res' network, so the two files do not describe "
            "the same model."
        )

    return companion


def _find_epanet_companions(res: Path) -> tuple[Path | None, Path | None]:
    """Find the ``.resx`` and ``.inp`` files sitting beside an EPANET ``.res``.

    A companion is recognised by sharing the result file's directory and stem.
    Either may be missing, in which case ``None`` takes its place.

    Parameters
    ----------
    res : Path
        Path to an EPANET ``.res`` result file.

    Returns
    -------
    tuple of (Path or None, Path or None)
        The ``.resx`` and ``.inp`` companions, in that order.
    """

    def sibling(suffix: str) -> Path | None:
        for candidate in sorted(res.parent.iterdir()):
            if (
                candidate.is_file()
                and candidate.stem == res.stem
                and candidate.suffix.lower() == suffix
            ):
                return candidate
        return None

    return sibling(".resx"), sibling(".inp")


def _suffix_of(companion: str | Path | Res1D) -> str:
    """Return a companion's lower-case extension, whatever form it arrives in.

    Parameters
    ----------
    companion : str, Path or Res1D
        A companion file, or one already opened.

    Returns
    -------
    str
        The extension, including its dot.
    """
    if isinstance(companion, Res1D):
        return Path(str(companion.file_path)).suffix.lower()
    return Path(companion).suffix.lower()


def _companion_paths(
    res: Res1D, companions: Sequence[str | Path | Res1D] | None
) -> tuple[list[str | Path | Res1D], bool]:
    """Decide which companions to read: the ones asked for, or the ones found.

    Parameters
    ----------
    res : Res1D
        The result file the companions belong to.
    companions : sequence of str, Path or Res1D, or None
        What the caller asked for. ``None`` means look beside the result file,
        an empty sequence means read none.

    Returns
    -------
    tuple of (list, bool)
        The companions to read, and whether they were found rather than named.
        The flag matters for error reporting: a file the caller never mentioned
        has to be named when it turns out to be the problem.

    Notes
    -----
    Only an EPANET ``.res`` is looked beside. A ``.res1d`` sitting next to an
    unrelated ``.inp`` of the same stem would otherwise take its reach lengths
    from another model's input file.
    """
    if companions is not None:
        return list(companions), False

    file_path = res.file_path
    if file_path is None or _suffix_of(str(file_path)) not in _COMPANION_SEARCH_EXTENSIONS:
        return [], False

    found = [path for path in _find_epanet_companions(Path(file_path)) if path is not None]
    return list(found), bool(found)


def _read_companions(
    res: Res1D, companions: Sequence[str | Path | Res1D]
) -> tuple[_Companion | None, dict[str, float] | None]:
    """Read the companions, sorting them by what each contributes.

    Parameters
    ----------
    res : Res1D
        The result file the companions belong to.
    companions : sequence of str, Path or Res1D
        The companions to read.

    Returns
    -------
    tuple of (_Companion or None, dict or None)
        Extra results and reach lengths, each None when no companion supplied it.

    Raises
    ------
    ValueError
        If an extension is not one a companion can have, or if two companions
        would supply the same thing.
    """
    extra: _Companion | None = None
    lengths: dict[str, float] | None = None

    for companion in companions:
        suffix = _suffix_of(companion)
        if suffix == ".resx":
            if extra is not None:
                raise ValueError("Two '.resx' companions were given; a network can read one.")
            extra = _open_companion_result(res, companion)
        elif suffix == ".inp":
            if lengths is not None:
                raise ValueError("Two '.inp' companions were given; a network can read one.")
            lengths = _read_companion_lengths(companion)
        else:
            raise ValueError(
                f"'{suffix}' is not a companion a network can read. Expected '.resx' for "
                "extra results or '.inp' for reach lengths."
            )

    return extra, lengths
