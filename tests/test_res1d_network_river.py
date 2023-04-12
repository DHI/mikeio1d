import os
import pytest
import numpy as np
import pandas as pd

from mikeio1d.res1d import Res1D
from mikeio1d.query import QueryDataStructure
from mikeio1d.query import QueryDataGlobal


@pytest.fixture
def test_file_path():
    test_folder_path = os.path.dirname(os.path.abspath(__file__))
    # Original file name was Exam6Base.res1d
    return os.path.join(test_folder_path, "testdata", "NetworkRiver.res1d")


@pytest.fixture(params=[False])
def test_file(test_file_path, request):
    return Res1D(test_file_path, lazy_load=request.param)


def test_read(test_file):
    df = test_file.read()
    assert len(df) == 73


def test_quantities(test_file):
    quantities = test_file.quantities
    assert len(quantities) == 13


def test_repr(test_file):
    res1d = test_file
    res1d_repr = res1d.__repr__()
    res1d_repr_ref = (
        '<mikeio1d.Res1D>\n' +
        'Start time: 2000-02-18 00:06:00\n' +
        'End time: 2000-02-18 12:06:00\n'
        '# Timesteps: 73\n' +
        '# Catchments: 0\n' +
        '# Nodes: 18\n' +
        '# Reaches: 18\n' +
        '# Globals: 4\n'
        '0 - WaterLevel <m>\n' +
        '1 - Discharge <m^3/s>\n' +
        '2 - ManningResistanceNumber <m^(1/3)/s>\n' +
        '3 - FlowVelocity <m/s>\n' +
        '4 - FlowVelocityInStructure <m/s>\n' +
        '5 - FlowAreaInStructure <m^2>\n' +
        '6 - DischargeInStructure <m^3/s>\n' +
        '7 - ControlStrategyId <Integer>\n' +
        '8 - GateLevel <m>\n' +
        '9 - Variable:TwoTimeSensorGateLevel <->\n' +
        '10 - Water level:Sensor:s.h.river53745.34 <m>\n' +
        '11 - Gate level:Sensor:SensorGateLevel <m>\n' +
        '12 - Discharge:Sensor:SensorGauge1 <m^3/s>'
    )
    assert res1d_repr == res1d_repr_ref


def test_data_item_dicts(test_file):
    res1d = test_file
    assert len(res1d.catchments) == 0
    assert len(res1d.nodes) == 18
    assert len(res1d.reaches) == 9
    assert len(res1d.global_data) == 4
    assert len(res1d.structures) == 10


@pytest.mark.parametrize("query,expected_max", [
    (QueryDataStructure("DischargeInStructure", "W_right"), 11.018),
    (QueryDataStructure("DischargeInStructure", "W_left_1_1"), 13.543),
    (QueryDataStructure("FlowAreaInStructure", "W_right"), 9.851),
    (QueryDataStructure("FlowAreaInStructure", "W_left_1_1"), 11.252)
])
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

    actual_max = round(df["DischargeInStructure:W_right:link_basin_right:18"].max(), 3)
    assert pytest.approx(actual_max) == 11.018

    actual_max = round(df["DischargeInStructure:W_left_1_1:link_basin_left:46"].max(), 3)
    assert pytest.approx(actual_max) == 13.543

    actual_max = round(df["FlowAreaInStructure:W_right:link_basin_right:18"].max(), 3)
    assert pytest.approx(actual_max) == 9.851

    actual_max = round(df["FlowAreaInStructure:W_left_1_1:link_basin_left:46"].max(), 3)
    assert pytest.approx(actual_max) == 11.252


@pytest.mark.parametrize("query,expected_max", [
    (QueryDataGlobal("Discharge:Sensor:SensorGauge1"), 77.522),
    (QueryDataGlobal("Gate level:Sensor:SensorGateLevel"), 53.770),
    (QueryDataGlobal("Variable:TwoTimeSensorGateLevel"), 107.54)
])
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

    assert len(df.columns) == 110

    max_water_level = round(df.max().max(), 3)
    assert pytest.approx(max_water_level) == 59.2


def test_all_structures_attributes(test_file):
    res1d = test_file
    res1d.structures.DischargeInStructure.add()
    df = res1d.read()

    assert len(df.columns) == 10

    max_discharge = round(df.max().max(), 3)
    assert pytest.approx(max_discharge) == 100.247


def test_res1d_modification(test_file):
    res1d = test_file

    # Test the reading of all the data into data frame
    df = res1d.read()
    max_value = round(df.max().max(), 3)

    # Check the overall maximum value
    assert pytest.approx(max_value) == 107.54

    # Test the modification of ResultData and
    # saving the modified data to a new res1d file.
    df2 = df.multiply(2.0)
    file_path = res1d.data.Connection.FilePath.Path
    file_path = file_path.replace('NetworkRiver.res1d', 'NetworkRiver.mod.res1d')
    res1d.modify(df2, file_path=file_path)

    df_mod = res1d.read()
    max_value_mod = round(df_mod.max().max(), 3)

    # Check the overall new maximum value (should be the previous max value time two)
    assert pytest.approx(max_value_mod) == 2.0 * max_value

    # Test the reading of modified file
    res1d_new = Res1D(file_path)
    df_new = res1d.read()
    max_value_new = round(df_mod.max().max(), 3)

    # Check the overall new maximum value again
    assert pytest.approx(max_value_new) == 2.0 * max_value


def test_res1d_modification_filtered(test_file):
    res1d = test_file

    # Test the reading of all the data into data frame
    df = res1d.read()
    max_value = round(df.max().max(), 3)

    df = df.drop(pd.date_range('2000-02-18 00:06:00', '2000-02-18 00:16:00', freq='10min'))
    df = df.drop(pd.date_range('2000-02-18 00:56:00', '2000-02-18 12:06:00', freq='10min'))

    # Test the modification of ResultData
    df2 = df.multiply(2.0)
    res1d.modify(df2)

    df_mod = res1d.read()
    max_value_mod = round(df_mod.max().max(), 3)

    # Check the overall new maximum value (should be the previous max value time two)
    assert pytest.approx(max_value_mod) == 2.0 * max_value

    # Modify the res1d data again, but only for flow velocity in structure
    res1d.structures.FlowVelocityInStructure.add()
    df = res1d.read()

    df = df.drop(pd.date_range('2000-02-18 00:06:00', '2000-02-18 00:16:00', freq='10min'))
    df = df.drop(pd.date_range('2000-02-18 00:56:00', '2000-02-18 12:06:00', freq='10min'))

    df2 = df.multiply(100.0)

    # Check the max value of flow velocity
    max_value_velocity = round(df2.max().max(), 3)
    assert pytest.approx(max_value_velocity) == 418.842

    res1d.modify(df2)
    res1d.clear_queries()
    df_mod = res1d.read()
    max_value_mod = round(df_mod.max().max(), 3)

    # Check the overall new maximum value, which should be determined by flow velocity
    assert pytest.approx(max_value_mod) == max_value_velocity
