"""ExtractorCsv class."""

from .extractor_txt import ExtractorTxt


class ExtractorCsv(ExtractorTxt):
    """Class which extracts data to comma separated value (CSV) file."""

    separator = ";"

    def set_output_format(self):
        """Set output format."""
        self.header1_format = "%s;"
        self.header2_format = "%s;"
        self.chainage_format = "%s;"
        self.chainage_formatcs = "{0:g}"
        self.data_format = "%s;"
        self.data_formatcs = "{0:g}"

    def write_item_type(self):
        """Write item type."""
        # Write CSV separator type
        self.f.write("sep=%s\n" % self.separator)
        ExtractorTxt.write_item_type(self)
