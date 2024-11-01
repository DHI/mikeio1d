"""ExtractorAll class."""

from .extractor_dfs0 import ExtractorDfs0
from .extractor_csv import ExtractorCsv
from .extractor_txt import ExtractorTxt


class ExtractorAll:
    """Class which extracts data into all supported file formats."""

    def __init__(self, out_file_name, output_data, result_data, time_step_skipping_number=1):
        self.all_extractors = [
            ExtractorTxt(
                out_file_name.replace(".-", ".txt"),
                output_data,
                result_data,
                time_step_skipping_number,
            ),
            ExtractorCsv(
                out_file_name.replace(".-", ".csv"),
                output_data,
                result_data,
                time_step_skipping_number,
            ),
            ExtractorDfs0(
                out_file_name.replace(".-", ".dfs0"),
                output_data,
                result_data,
                time_step_skipping_number,
            ),
        ]

    def export(self):
        """Export data to all supported file formats."""
        for extractor in self.all_extractors:
            extractor.export()
