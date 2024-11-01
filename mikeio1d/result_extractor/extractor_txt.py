"""ExtractorTxt class."""

from .extractor import Extractor

import System

from DHI.Mike1D.ResultDataAccess import ItemTypeGroup


class ExtractorTxt(Extractor):
    """Class which extracts data to text file."""

    def export(self):
        """Export data to text file."""
        self.f = open(self.out_file_name, "w")
        self.set_output_format()
        self.write_item_type()
        self.write_quantity()
        self.write_name()
        self.write_chainage()
        self.write_data_items()
        self.f.close()

    def set_output_format(self):
        """Set output format."""
        self.header1_format = "%-20s"
        self.header2_format = "%15s"
        self.chainage_format = "%15s"
        self.chainage_formatcs = "{0,15:0.00}"
        self.data_format = "%15s"
        self.data_formatcs = "{0,15:0.000000}"

    def write_item_type(self):
        """Write item type."""
        output_data, f = self.output_data, self.f
        header1_format, header2_format = self.header1_format, self.header2_format

        f.write(header1_format % "Type")
        for data_entry in output_data:
            item_type_group = data_entry.data_item.ItemTypeGroup

            if item_type_group == ItemTypeGroup.ReachItem:
                f.write(header2_format % "Reach")

            elif item_type_group == ItemTypeGroup.NodeItem:
                f.write(header2_format % "Node")

            elif item_type_group == ItemTypeGroup.CatchmentItem:
                f.write(header2_format % "Catchment")

            else:
                f.write(header2_format % item_type_group)
        f.write("\n")

    def write_quantity(self):
        """Write quantity."""
        output_data, f = self.output_data, self.f
        header1_format, header2_format = self.header1_format, self.header2_format

        f.write(header1_format % "Quantity")
        for data_entry in output_data:
            (f.write(header2_format % data_entry.data_item.Quantity.Id),)
        f.write("\n")

    def write_name(self):
        """Write name."""
        output_data, f = self.output_data, self.f
        result_data = self.result_data
        header1_format, header2_format = self.header1_format, self.header2_format

        (f.write(header1_format % "Name"),)
        nodes = list(result_data.Nodes)
        reaches = list(result_data.Reaches)
        catchments = list(result_data.Catchments)
        for data_entry in output_data:
            data_item = data_entry.data_item
            item_type_group = data_item.ItemTypeGroup
            number_within_group = data_item.NumberWithinGroup

            if item_type_group == ItemTypeGroup.ReachItem:
                (f.write(header2_format % reaches[number_within_group].Name),)

            elif item_type_group == ItemTypeGroup.NodeItem:
                (f.write(header2_format % nodes[number_within_group].Id),)

            elif item_type_group == ItemTypeGroup.CatchmentItem:
                (f.write(header2_format % catchments[number_within_group].Id),)

            else:
                (f.write(header2_format % "-"),)
        f.write("\n")

    def write_chainage(self):
        """Write chainage."""
        output_data, f = self.output_data, self.f
        result_data = self.result_data
        header1_format, header2_format = self.header1_format, self.header2_format
        chainage_format, chainage_formatcs = self.chainage_format, self.chainage_formatcs

        (f.write(header1_format % "Chainage"),)
        for data_entry in output_data:
            data_item = data_entry.data_item
            element_index = data_entry.element_index

            if data_item.ItemTypeGroup != ItemTypeGroup.ReachItem or data_item.IndexList is None:
                (f.write(header2_format % "-"),)
                continue

            index_list = list(data_item.IndexList)
            reaches = list(result_data.Reaches)
            gridpoints = list(reaches[data_item.NumberWithinGroup].GridPoints)
            gridpoint_index = index_list[element_index]
            (
                f.write(
                    chainage_format
                    % System.String.Format(chainage_formatcs, gridpoints[gridpoint_index].Chainage)
                ),
            )

        f.write("\n")

    def write_data_items(self):
        """Write data items."""
        output_data, f = self.output_data, self.f
        result_data = self.result_data
        header1_format, data_format, data_formatcs = (
            self.header1_format,
            self.data_format,
            self.data_formatcs,
        )

        times = list(result_data.TimesList)
        # Write data
        for time_step_index in range(result_data.NumberOfTimeSteps):
            if time_step_index % self.time_step_skipping_number != 0:
                continue

            time = times[time_step_index]
            (f.write(header1_format % (time.ToString("yyyy-MM-dd HH:mm:ss"))),)
            for data_entry in output_data:
                data_item = data_entry.data_item
                element_index = data_entry.element_index
                value = data_item.GetValue(time_step_index, element_index)
                (f.write(data_format % System.String.Format(data_formatcs, value)),)
            f.write("\n")
