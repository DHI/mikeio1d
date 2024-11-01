"""Extractor class."""


class Extractor:
    """Base class for data extractors to specified file format."""

    def __init__(self, out_file_name, output_data, result_data, time_step_skipping_number=1):
        self.out_file_name = out_file_name
        self.output_data = output_data
        self.result_data = result_data
        self.time_step_skipping_number = time_step_skipping_number
