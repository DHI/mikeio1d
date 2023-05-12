from .extractor_all import ExtractorAll
from .extractor_dfs0 import ExtractorDfs0
from .extractor_csv import ExtractorCsv
from .extractor_txt import ExtractorTxt


class ExtractorOutputFileType:
    TXT = 'txt'
    CSV = 'csv'
    DFS0 = 'dfs0'
    ALL = '-'


class ExtractorCreator:
    """ Class which creates an ResultData time series extractors """

    @staticmethod
    def create(out_file_type, out_file_name, output_data, result_data, time_step_skipping_number=1):
        extractors = {
            ExtractorOutputFileType.TXT: ExtractorTxt,
            ExtractorOutputFileType.CSV: ExtractorCsv,
            ExtractorOutputFileType.DFS0: ExtractorDfs0,
            ExtractorOutputFileType.ALL: ExtractorAll
        }

        extractor = extractors.get(out_file_type, None)

        return extractor(out_file_name, output_data, result_data, time_step_skipping_number)
