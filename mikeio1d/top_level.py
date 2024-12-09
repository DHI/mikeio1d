"""Module containing top level functions for MIKE IO 1D."""

from __future__ import annotations

from pathlib import Path

from .res1d import Res1D
from .xns11 import Xns11


def open(file_name: str | Path, **kwargs) -> Res1D | Xns11:
    """Open a file type supported by MIKE IO 1D file.

    Parameters
    ----------
    file_name : str or Path
        Path to the file to read.
    **kwargs
        Additional keyword arguments to pass to the relevant constructor.

    See Also
    --------
    mikeio1d.Res1D
    mikeio1d.Xns11

    Returns
    -------
    Res1D or Xns11
        The object representing the 1D file.

    Examples
    --------
    >>> import mikeio1d
    >>> res = mikeio1d.open("results.res1d")
    >>> res.nodes.read()

    >>> xs = mikeio1d.open("cross_section.xns11")
    >>> xs
    """
    if isinstance(file_name, str):
        file_name = Path(file_name)

    if not file_name.exists():
        raise FileNotFoundError(f"File not found: {file_name}")

    suffix = file_name.suffix.lower()
    file_name = str(file_name)

    if suffix in Res1D.get_supported_file_extensions():
        return Res1D(file_name, **kwargs)
    elif suffix in Xns11.get_supported_file_extensions():
        return Xns11(file_name, **kwargs)
