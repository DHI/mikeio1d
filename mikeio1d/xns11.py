"""Module for the Xns11 class."""

from __future__ import annotations

from collections import defaultdict, namedtuple
from pathlib import Path
from warnings import warn

import pandas as pd
from DHI.Mike1D.Generic import Location

from .cross_sections import CrossSection
from .cross_sections import CrossSectionCollection


class Xns11(CrossSectionCollection):
    """A class to read and write xns11 files.

    Parameters
    ----------
    file_path: str or Path, optional
        full path and file name to the xns11 file.

    Notes
    -----
    The Xns11 class is a subclass of CrossSectionCollection. The main difference is that Xns11 has a file_path property
    to track where the file was last loaded from or saved to.

    Examples
    --------
    ```python
    # Open an existing file
    >>> xns = Xns11("file.xns11")

    # Overview of the cross sections
    >>> xns.to_dataframe()

    # Read a specific cross section
    >>> xs = xns.sel(location_id='basin_left1', chainage='122.042', topo_id='1')

    # Plot a cross section
    >>> xs.plot()

    # Access cross section raw data
    >>> xs.raw_data

    # Access cross section processed data
    >>> xs.processed_data
    ```

    """

    def __init__(self, file_path: str | Path = None, *args, **kwargs):
        if file_path and not isinstance(file_path, (str, Path)):
            self._file_path = None
            first_arg = file_path
            args = (first_arg, *args)
        elif file_path:
            self._file_path = Path(file_path)
        else:
            self._file_path = None

        super().__init__(*args, **kwargs)

        if self._file_path:
            self._init_from_xns11(self._file_path)

    @staticmethod
    def get_supported_file_extensions() -> set[str]:
        """Get supported file extensions for Xns11."""
        return {".xns11"}

    @staticmethod
    def from_cross_section_collection(xsections: CrossSectionCollection) -> Xns11:
        """Create a Xns11 object from a CrossSectionCollection."""
        xns = Xns11()
        xns._init_from_cross_section_data(xsections._cross_section_data)
        return xns

    @property
    def file_path(self) -> Path | None:
        """Full path and file name to the xns11 file."""
        return self._file_path

    def write(self, file_path: str | Path = None) -> None:
        """Write cross section data to an xns11 file.

        Parameters
        ----------
        file_path: str or Path, optional
            Full file path of the xns11 file to be written. Default is the file_path used to open the file.
        """
        if file_path:
            self._file_path = Path(file_path)

        if not self._file_path:
            raise ValueError(
                "No 'file_path' to write to. Set 'file_path' or pass it as an argument."
            )

        self.to_xns11(self._file_path)


__all__ = ["Xns11"]
