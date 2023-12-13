from System.Collections.Generic import List
from System import String

from DHI.Mike1D.MikeIO import LTSResultMerger


class ResultMerger:
    """
    Wrapper class for merging res1d result files.

    Parameters
    ----------
    file_names : list of str
        List of res1d file names to merge.

    """

    def __init__(self, file_names):
        self.file_names = file_names
        self.result_data_merged = None

    def merge(self, merged_file_name):
        """
        Merges the data from in file_names to a file
        specified by merged_file_name.

        Parameters
        ----------
        merged_file_name : str
            File name of the res1d file to store the merged data.
        """
        if self.result_data_merged is None:
            file_names_dotnet = self._get_file_name_dotnet()
            self.result_data_merged = LTSResultMerger.Merge(file_names_dotnet)

        self.result_data_merged.Connection.FilePath.Path = merged_file_name
        self.result_data_merged.Save()

    def _get_file_name_dotnet(self):
        file_names_dotnet = List[String]()
        for file_name in self.file_names:
            file_names_dotnet.Add(file_name)
        return file_names_dotnet
