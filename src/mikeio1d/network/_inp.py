"""Minimal reader for EPANET and SWMM ``.inp`` input files.

The binary result readers do not touch the ``.inp`` that accompanies a result
file, so it is parsed here. Both products use the same layout: bracketed
section headers, ``;``-prefixed comments (including the ``;;Name  Node1 ...``
column headers the products write), whitespace-delimited data rows, and blank
lines to ignore.

Only the sections a network needs are interpreted; everything else is kept as
raw fields for a caller to use, or ignored.
"""

from __future__ import annotations

from pathlib import Path


def read_sections(path: str | Path) -> dict[str, list[list[str]]]:
    """Parse an ``.inp`` file into its sections.

    Parameters
    ----------
    path : str or Path
        Path to an EPANET or SWMM ``.inp`` file.

    Returns
    -------
    dict[str, list[list[str]]]
        Section name (upper case, without brackets) mapped to its data rows,
        each row split into whitespace-delimited fields. Comment-only and blank
        lines are dropped, as is any trailing comment on a data row.

    Examples
    --------
    >>> sections = read_sections("model.inp")  # doctest: +SKIP
    >>> sections["PIPES"][0]  # doctest: +SKIP
    ['10', '10', '11', '3209.544', '304.8', '100', '0', 'Open']
    """
    sections: dict[str, list[list[str]]] = {}
    current: list[list[str]] | None = None

    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            # A comment can trail a data row, so strip it before anything else.
            line = line.split(";", 1)[0].strip()
            if not line:
                continue

            if line.startswith("["):
                name = line.strip("[]").strip().upper()
                current = sections.setdefault(name, [])
                continue

            if current is not None:
                current.append(line.split())

    return sections


def read_pipe_lengths(path: str | Path) -> dict[str, float]:
    """Read reach lengths from the ``[PIPES]`` section of an EPANET ``.inp``.

    Parameters
    ----------
    path : str or Path
        Path to an EPANET ``.inp`` file.

    Returns
    -------
    dict[str, float]
        Pipe ID mapped to its length. Pumps and valves are links too, but carry
        no length, so they are absent from the result rather than present with a
        placeholder.

    Raises
    ------
    ValueError
        If the file has no ``[PIPES]`` section, or a row there has too few
        fields to read a length from.

    Notes
    -----
    ``[PIPES]`` rows are ``ID Node1 Node2 Length Diameter Roughness ...``, so the
    length is the fourth field. The units are whatever the model declares in
    ``[OPTIONS]``; no conversion is applied.
    """
    sections = read_sections(path)

    try:
        rows = sections["PIPES"]
    except KeyError:
        raise ValueError(
            f"'{path}' has no [PIPES] section, so it does not look like an "
            "EPANET input file. Available sections: "
            f"{sorted(sections)}."
        )

    _ID, _LENGTH = 0, 3
    lengths: dict[str, float] = {}
    for row in rows:
        if len(row) <= _LENGTH:
            raise ValueError(
                f"Cannot read a pipe length from [PIPES] row {' '.join(row)!r} "
                f"in '{path}': expected at least {_LENGTH + 1} fields "
                f"(ID, Node1, Node2, Length), got {len(row)}."
            )
        lengths[row[_ID]] = float(row[_LENGTH])

    return lengths
