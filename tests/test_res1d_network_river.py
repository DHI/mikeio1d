import os
import pytest
import pandas as pd
import matplotlib as mpl

# Avoid problems with matplotlib when running on a server without a display
mpl.use("Agg")

from mikeio1d.res1d import Res1D
from mikeio1d.query import QueryDataStructure
from mikeio1d.query import QueryDataGlobal
from mikeio1d.result_reader_writer.result_reader import ColumnMode


@pytest.fixture
def test_file_path():
    test_folder_path = os.path.dirname(os.path.abspath(__file__))
    # Original file name was Exam6Base.res1d
    return os.path.join(test_folder_path, "testdata", "network_river.res1d")


@pytest.fixture(params=[False])
def test_file(test_file_path, request):
    return Res1D(test_file_path, lazy_load=request.param)


def test_read(test_file):
    df = test_file.read()
    assert len(df) == 73
    # TODO: assert not df.columns.duplicated().any() - add this, but it fails since columns are not guaranteed unique


def test_quantities(test_file):
    quantities = test_file.quantities
    assert len(quantities) == 13


def test_repr(test_file):
    res1d = test_file
    res1d_info = res1d._get_info()
    res1d_info_ref = (
        "Start time: 2000-02-18 00:06:00\n"
        + "End time: 2000-02-18 12:06:00\n"
        + "# Timesteps: 73\n"
        + "# Catchments: 0\n"
        + "# Nodes: 18\n"
        + "# Reaches: 18\n"
        + "# Globals: 4\n"
        + "0 - WaterLevel <m>\n"
        + "1 - Discharge <m^3/s>\n"
        + "2 - ManningResistanceNumber <m^(1/3)/s>\n"
        + "3 - FlowVelocity <m/s>\n"
        + "4 - FlowVelocityInStructure <m/s>\n"
        + "5 - FlowAreaInStructure <m^2>\n"
        + "6 - DischargeInStructure <m^3/s>\n"
        + "7 - ControlStrategyId <Integer>\n"
        + "8 - GateLevel <m>\n"
        + "9 - Variable:TwoTimeSensorGateLevel <->\n"
        + "10 - Water level:Sensor:s.h.river53745.34 <m>\n"
        + "11 - Gate level:Sensor:SensorGateLevel <m>\n"
        + "12 - Discharge:Sensor:SensorGauge1 <m^3/s>"
    )
    assert res1d_info == res1d_info_ref


def test_data_item_dicts(test_file):
    res1d = test_file
    assert len(res1d.catchments) == 0
    assert len(res1d.nodes) == 18
    assert len(res1d.reaches) == 9
    assert len(res1d.global_data) == 4
    assert len(res1d.structures) == 10


@pytest.mark.parametrize(
    "query,expected_max",
    [
        (QueryDataStructure("DischargeInStructure", "W_right"), 11.018),
        (QueryDataStructure("DischargeInStructure", "W_left_1_1"), 13.543),
        (QueryDataStructure("FlowAreaInStructure", "W_right"), 9.851),
        (QueryDataStructure("FlowAreaInStructure", "W_left_1_1"), 11.252),
    ],
)
def test_read_structures_with_queries(test_file, query, expected_max):
    data = test_file.read(query)
    assert pytest.approx(round(data.max().values[0], 3)) == expected_max


def test_structure_attributes(test_file):
    res1d = test_file
    structures = res1d.structures

    structures.W_right.DischargeInStructure.add()

    structures.W_left_1_1.DischargeInStructure.add()

    structures.W_right.FlowAreaInStructure.add()

    structures.W_left_1_1.FlowAreaInStructure.add()

    df = res1d.read()

    column_mode = res1d.result_reader.column_mode

    if column_mode in (ColumnMode.ALL, ColumnMode.COMPACT):
        actual_max = round(
            df.T.query(
                "quantity=='DischargeInStructure' and name=='W_right:link_basin_right' and chainage==18"
            ).T.max(),
            3,
        )
    elif column_mode == ColumnMode.STRING:
        actual_max = round(df["DischargeInStructure:W_right:link_basin_right:18"].max(), 3)
    assert pytest.approx(actual_max) == 11.018

    if column_mode in (ColumnMode.ALL, ColumnMode.COMPACT):
        actual_max = round(
            df.T.query(
                "quantity=='DischargeInStructure' and name=='W_left_1_1:link_basin_left' and chainage==46"
            ).T.max(),
            3,
        )
    elif column_mode == ColumnMode.STRING:
        actual_max = round(df["DischargeInStructure:W_left_1_1:link_basin_left:46"].max(), 3)
    assert pytest.approx(actual_max) == 13.543

    if column_mode == ColumnMode.ALL:
        actual_max = round(
            df.T.query(
                "quantity=='FlowAreaInStructure' and name=='W_right:link_basin_right' and chainage==18"
            ).T.max(),
            3,
        )
    elif column_mode == ColumnMode.STRING:
        actual_max = round(df["FlowAreaInStructure:W_right:link_basin_right:18"].max(), 3)
    assert pytest.approx(actual_max) == 9.851

    if column_mode in (ColumnMode.ALL, ColumnMode.COMPACT):
        actual_max = round(
            df.T.query(
                "quantity=='FlowAreaInStructure' and name=='W_left_1_1:link_basin_left' and chainage==46"
            ).T.max(),
            3,
        )
    elif column_mode == ColumnMode.STRING:
        actual_max = round(df["FlowAreaInStructure:W_left_1_1:link_basin_left:46"].max(), 3)
    assert pytest.approx(actual_max) == 11.252


def test_structure_reach_attributes(test_file):
    res1d = test_file
    structures = res1d.structures

    structures.link_links_1_2_LinkChannel.Discharge.add()
    structures.link_links_2_2_LinkChannel.Discharge.add()

    df = res1d.read()

    max_discharge = round(df.max().max(), 3)
    assert pytest.approx(max_discharge) == 0.0


@pytest.mark.parametrize(
    "query,expected_max",
    [
        (QueryDataGlobal("Discharge:Sensor:SensorGauge1"), 77.522),
        (QueryDataGlobal("Gate level:Sensor:SensorGateLevel"), 53.770),
        (QueryDataGlobal("Variable:TwoTimeSensorGateLevel"), 107.54),
    ],
)
def test_read_global_items_with_queries(test_file, query, expected_max):
    data = test_file.read(query)
    assert pytest.approx(round(data.max().values[0], 3)) == expected_max


def test_global_data_attributes(test_file):
    res1d = test_file
    global_data = res1d.global_data

    global_data.Discharge_Sensor_SensorGauge1.add()
    global_data.Gate_level_Sensor_SensorGateLevel.add()
    global_data.Variable_TwoTimeSensorGateLevel.add()

    df = res1d.read()

    actual_max = round(df["Discharge:Sensor:SensorGauge1"].max(), 3)
    assert pytest.approx(actual_max) == 77.522

    actual_max = round(df["Gate level:Sensor:SensorGateLevel"].max(), 3)
    assert pytest.approx(actual_max) == 53.770

    actual_max = round(df["Variable:TwoTimeSensorGateLevel"].max(), 3)
    assert pytest.approx(actual_max) == 107.54


def test_all_nodes_attributes(test_file):
    res1d = test_file
    res1d.nodes.WaterLevel.add()
    df = res1d.read()

    assert len(df.columns) == 18

    max_water_level = round(df.max().max(), 3)
    assert pytest.approx(max_water_level) == 59.200


def test_all_reach_attributes(test_file):
    res1d = test_file
    res1d.reaches.link_basin_left1_2.WaterLevel.add()
    df = res1d.read()

    assert len(df.columns) == 2

    max_water_level = round(df.max().max(), 3)
    assert pytest.approx(max_water_level) == 57.795


def test_all_reaches_attributes(test_file):
    res1d = test_file
    res1d.reaches.WaterLevel.add()
    df = res1d.read()

    # Previously was 110, now includes some duplicates that were missed
    assert len(df.columns) == 119

    max_water_level = round(df.max().max(), 3)
    assert pytest.approx(max_water_level) == 59.2


def test_all_structures_attributes(test_file):
    res1d = test_file
    res1d.structures.DischargeInStructure.add()
    df = res1d.read()

    assert len(df.columns) == 10

    max_discharge = round(df.max().max(), 3)
    assert pytest.approx(max_discharge) == 100.247


@pytest.mark.parametrize(
    "column_mode, expected_exception",
    [(ColumnMode.ALL, None), (ColumnMode.TIMESERIES, None), (ColumnMode.STRING, ValueError)],
)
def test_res1d_modification(test_file, column_mode, expected_exception):
    res1d = test_file
    res1d.result_reader.column_mode = column_mode

    # Test the reading of all the data into data frame
    df = res1d.read()
    max_value = round(df.max().max(), 3)

    # Check the overall maximum value
    assert pytest.approx(max_value) == 107.54

    # Test the modification of ResultData and
    # saving the modified data to a new res1d file.
    df2 = df.multiply(2.0)
    file_path = res1d.data.Connection.FilePath.Path
    file_path = file_path.replace("network_river.res1d", "network_river.mod.res1d")

    if expected_exception is not None:
        with pytest.raises(expected_exception):
            res1d.modify(df2, file_path=file_path)
        return

    res1d.modify(df2, file_path=file_path)

    df_mod = res1d.read()
    max_value_mod = round(df_mod.max().max(), 3)

    # Check the overall new maximum value (should be the previous max value time two)
    assert pytest.approx(max_value_mod) == 2.0 * max_value

    # Test the reading of modified file
    res1d_new = Res1D(file_path)
    df_new = res1d_new.read()
    max_value_new = round(df_new.max().max(), 3)

    # Check the overall new maximum value again
    assert pytest.approx(max_value_new) == 2.0 * max_value


@pytest.mark.parametrize(
    "column_mode, expected_exception",
    [(ColumnMode.ALL, None), (ColumnMode.TIMESERIES, None), (ColumnMode.STRING, ValueError)],
)
def test_res1d_modification_filtered(test_file, column_mode, expected_exception):
    res1d = test_file
    res1d.result_reader.column_mode = column_mode

    # Test the reading of all the data into data frame
    df = res1d.read()
    max_value = round(df.max().max(), 3)

    df = df.drop(pd.date_range("2000-02-18 00:06:00", "2000-02-18 00:16:00", freq="10min"))
    df = df.drop(pd.date_range("2000-02-18 00:56:00", "2000-02-18 12:06:00", freq="10min"))

    # Test the modification of ResultData
    df2 = df.multiply(2.0)

    if expected_exception is not None:
        with pytest.raises(expected_exception):
            res1d.modify(df2)
        return

    res1d.modify(df2)

    df_mod = res1d.read()
    max_value_mod = round(df_mod.max().max(), 3)

    # Check the overall new maximum value (should be the previous max value time two)
    assert pytest.approx(max_value_mod) == 2.0 * max_value

    # Modify the res1d data again, but only for flow velocity in structure
    res1d.structures.FlowVelocityInStructure.add()
    df = res1d.read()

    df = df.drop(pd.date_range("2000-02-18 00:06:00", "2000-02-18 00:16:00", freq="10min"))
    df = df.drop(pd.date_range("2000-02-18 00:56:00", "2000-02-18 12:06:00", freq="10min"))

    df2 = df.multiply(100.0)

    # Check the max value of flow velocity
    max_value_velocity = round(df2.max().max(), 3)
    assert pytest.approx(max_value_velocity) == 418.842

    res1d.modify(df2)
    df_mod = res1d.read()
    max_value_mod = round(df_mod.max().max(), 3)

    # Check the overall new maximum value, which should be determined by flow velocity
    assert pytest.approx(max_value_mod) == max_value_velocity


def test_extraction_to_csv_dfs0_txt(test_file):
    res1d = test_file
    res1d.clear_queue_after_reading = False

    res1d.reaches.WaterLevel.add()
    res1d.nodes.WaterLevel.add()

    file_path = res1d.data.Connection.FilePath.Path

    file_path_csv = file_path.replace("network_river.res1d", "network_river.extract.csv")
    res1d.to_csv(file_path_csv, time_step_skipping_number=10)
    file_size_csv = 24819  # originally 21905, however that missed some data items
    assert 0.5 * file_size_csv < os.stat(file_path_csv).st_size < 2.0 * file_size_csv

    file_path_dfs0 = file_path.replace("network_river.res1d", "network_river.extract.dfs0")
    res1d.to_dfs0(file_path_dfs0, time_step_skipping_number=10)
    file_size_dfs0 = 32388  # originally 30302, however that missed some data items
    assert file_size_dfs0 - 1000 < os.stat(file_path_dfs0).st_size < file_size_dfs0 + 1000

    file_path_txt = file_path.replace("network_river.res1d", "network_river.extract.txt")
    res1d.to_txt(file_path_txt, time_step_skipping_number=10)
    file_size_txt = 25008  # originally 23400. however that missed some data items
    assert 0.5 * file_size_txt < os.stat(file_path_txt).st_size < 2.0 * file_size_txt


def test_result_quantity_methods(test_file):
    res1d = test_file
    file_path = res1d.data.Connection.FilePath.Path
    discharge_in_structure = res1d.structures.W_right.DischargeInStructure

    df = discharge_in_structure.to_dataframe()
    max_value = round(df.max().iloc[0], 3)
    assert pytest.approx(max_value) == 11.018

    # Test the calling of methods
    discharge_in_structure.plot()
    discharge_in_structure.to_csv(
        file_path.replace("network_river.res1d", "w_right_discharge_in_structure.extract.csv")
    )
    discharge_in_structure.to_dfs0(
        file_path.replace("network_river.res1d", "w_right_discharge_in_structure.extract.dfs0")
    )
    discharge_in_structure.to_txt(
        file_path.replace("network_river.res1d", "w_right_discharge_in_structure.extract.txt")
    )


def test_result_quantity_collection_methods(test_file):
    res1d = test_file
    file_path = res1d.data.Connection.FilePath.Path
    discharge_in_structure = res1d.structures.DischargeInStructure

    df = discharge_in_structure.to_dataframe()
    max_value = round(df.max().max(), 3)
    assert pytest.approx(max_value) == 100.247

    # Test the calling of methods
    ax = discharge_in_structure.plot()
    discharge_in_structure.plot(ax=ax)

    discharge_in_structure.to_csv(
        file_path.replace("network_river.res1d", "discharge_in_structure.extract.csv")
    )
    discharge_in_structure.to_dfs0(
        file_path.replace("network_river.res1d", "discharge_in_structure.extract.dfs0")
    )
    discharge_in_structure.to_txt(
        file_path.replace("network_river.res1d", "discharge_in_structure.extract.txt")
    )


def test_calculate_total_reach_lengths(res1d_river_network):
    reach = res1d_river_network.result_network.reaches.river
    assert reach._get_total_length() == pytest.approx(2024.22765)
