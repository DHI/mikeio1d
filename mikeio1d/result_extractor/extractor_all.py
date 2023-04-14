from .extractor_dfs0 import ExtractorDfs0
from .extractor_csv import ExtractorCsv
from .extractor_txt import ExtractorTxt


class OutputFileType(object):
    TXT = 'txt'
    CSV = 'csv'
    DFS0 = 'dfs0'
    ALL = '-'


class ExtractorAll(object):
    """Class which extracts data into all supported file formats"""

    def __init__(self, out_file_name, output_data, result_data, time_step_skipping_number=1):
        self.all_extractors = [
            ExtractorTxt(out_file_name.replace(".-", ".txt"), output_data, result_data, time_step_skipping_number),
            ExtractorCsv(out_file_name.replace(".-", ".csv"), output_data, result_data, time_step_skipping_number),
            ExtractorDfs0(out_file_name.replace(".-", ".dfs0"), output_data, result_data, time_step_skipping_number)
        ]

    @staticmethod
    def create(out_file_type, out_file_name, output_data, result_data, time_step_skipping_number=1):
        if out_file_type == OutputFileType.TXT:
            return ExtractorTxt(out_file_name, output_data, result_data, time_step_skipping_number)

        elif out_file_type == OutputFileType.CSV:
            return ExtractorCsv(out_file_name, output_data, result_data, time_step_skipping_number)

        elif out_file_type == OutputFileType.DFS0:
            return ExtractorDfs0(out_file_name, output_data, result_data, time_step_skipping_number)

        elif out_file_type == OutputFileType.ALL:
            return ExtractorAll(out_file_name, output_data, result_data, time_step_skipping_number)

        return None

    def export(self):
        for extractor in self.all_extractors:
            extractor.export()
