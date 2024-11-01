"""ExtractorDfs0 class."""

from .extractor import Extractor

import System
from System import Array

from DHI.Generic.MikeZero import eumUnit
from DHI.Generic.MikeZero.DFS import DfsFactory
from DHI.Generic.MikeZero.DFS import DfsBuilder
from DHI.Generic.MikeZero.DFS import DfsSimpleType
from DHI.Generic.MikeZero.DFS import DataValueType
from DHI.Generic.MikeZero.DFS import StatType

from DHI.Mike1D.ResultDataAccess import ItemTypeGroup


class ExtractorDfs0(Extractor):
    """Class which extracts data to dfs0 file format."""

    def export(self):
        """Export data to dfs0 file."""
        self.factory = DfsFactory()
        self.builder = self.create_dfs_builder()
        self.define_dynamic_data_items()
        self.write_data_items()

    def create_dfs_builder(self):
        """Create dfs builder."""
        result_data = self.result_data
        factory = self.factory

        builder = DfsBuilder.Create("mikeio1d", "MIKE SDK", 100)

        # Set up file header
        builder.SetDataType(1)
        builder.SetGeographicalProjection(factory.CreateProjectionUndefined())
        builder.SetTemporalAxis(
            factory.CreateTemporalNonEqCalendarAxis(eumUnit.eumUsec, result_data.StartTime)
        )
        builder.SetItemStatisticsType(StatType.NoStat)

        return builder

    def define_dynamic_data_items(self):
        """Define dynamic data items."""
        output_data = self.output_data
        result_data = self.result_data
        builder = self.builder

        for data_entry in output_data:
            data_item = data_entry.data_item
            element_index = data_entry.element_index

            quantity = data_item.Quantity
            item_type_group = data_item.ItemTypeGroup
            number_within_group = data_item.NumberWithinGroup

            reaches = list(result_data.Reaches)
            nodes = list(result_data.Nodes)
            catchments = list(result_data.Catchments)

            if item_type_group == ItemTypeGroup.ReachItem:
                reach = reaches[number_within_group]
                gridpoint_index = data_item.IndexList[element_index]
                gridpoints = list(reach.GridPoints)
                chainage = gridpoints[gridpoint_index].Chainage
                item_name = "reach:%s:%s:%.3f" % (quantity.Id, reach.Name, chainage)

            elif item_type_group == ItemTypeGroup.NodeItem:
                node = nodes[number_within_group]
                item_name = "node:%s:%s" % (quantity.Id, node.Id)

            elif item_type_group == ItemTypeGroup.CatchmentItem:
                catchment = catchments[number_within_group]
                item_name = "catchment:%s:%s" % (quantity.Id, catchment.Id)

            else:
                item_name = "%s:%s:%s" % (item_type_group, quantity.Id, data_item.Id)

            item = builder.CreateDynamicItemBuilder()
            item.Set(item_name, data_item.Quantity.EumQuantity, DfsSimpleType.Float)
            item.SetValueType(DataValueType.Instantaneous)
            item.SetAxis(self.factory.CreateAxisEqD0())
            builder.AddDynamicItem(item.GetDynamicItemInfo())

    def write_data_items(self):
        """Write data items."""
        output_data = self.output_data
        result_data = self.result_data
        builder = self.builder

        # Create file
        builder.CreateFile(self.out_file_name)
        dfsfile = builder.GetFile()
        times = list(result_data.TimesList)

        # Write data to file
        val = Array.CreateInstance(System.Single, 1)
        for time_step_index in range(result_data.NumberOfTimeSteps):
            if time_step_index % self.time_step_skipping_number != 0:
                continue

            time = times[time_step_index].Subtract(result_data.StartTime).TotalSeconds
            for data_entry in output_data:
                data_item = data_entry.data_item
                element_index = data_entry.element_index

                val[0] = data_item.GetValue(time_step_index, element_index)
                dfsfile.WriteItemTimeStepNext(time, val)

        dfsfile.Close()
