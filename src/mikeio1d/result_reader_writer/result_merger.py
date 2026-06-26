"""Module for ResultMerger class."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from typing import List

from System.Collections.Generic import List as DotNetList
from System import String

from DHI.Mike1D.MikeIO import ResultMerger as Res1DResultMerger


class ResultMerger:
    """Wrapper class for merging res1d result files.

    Parameters
    ----------
    file_names : list of str
        List of res1d file names to merge.

    """

    def __init__(self, file_names: List[str]):
        self.file_names = file_names

    def merge(self, merged_file_name: str):
        """Merge the data from in file_names to a file specified by merged_file_name.

        Parameters
        ----------
        merged_file_name : str
            File name of the res1d file to store the merged data.

        """
        file_names_dotnet = self._get_file_name_dotnet()
        Res1DResultMerger.Merge(file_names_dotnet, merged_file_name)

    def _get_file_name_dotnet(self):
        file_names_dotnet = DotNetList[String]()
        for file_name in self.file_names:
            file_names_dotnet.Add(file_name)
        return file_names_dotnet
