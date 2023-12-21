import pandas as pd
import platform
import clr
import System

from mikeio1d.dotnet import from_dotnet_datetime
from mikeio1d.dotnet import to_dotnet_datetime


def test_from_dotnet_datetime_preserves_millisecond_precision():
    dtstr = "2021-01-01 00:00:00.123"

    dotnet_dt = System.DateTime.Parse(dtstr)
    assert dotnet_dt.Millisecond == 123
    py_dt = from_dotnet_datetime(dotnet_dt)
    # python datetime doesn't have a millisecond property so we use microsecond
    assert py_dt.microsecond == 123000


def test_to_dotnet_datetime_preserves_millisecond_precision():
    # Write the same test as above, but in the reverse direction
    dtstr = "2021-01-01 00:00:00.123"

    py_dt = pd.to_datetime(dtstr)
    assert py_dt.microsecond == 123000
    dotnet_dt = to_dotnet_datetime(py_dt)
    assert dotnet_dt.Millisecond == 123


def test_datetime_conversions_preserve_microsecond_ticks():
    ticks = 629118741618712340
    dotnet_time = System.DateTime(ticks)

    python_time = from_dotnet_datetime(dotnet_time, round_to_milliseconds=False)
    assert python_time.microsecond == 871234

    dotnet_time_final = to_dotnet_datetime(python_time)
    assert dotnet_time_final.Ticks == ticks


def test_dotnet_add_seconds_ticks():
    ticks = 629118741000000000
    time = System.DateTime(ticks)

    assert time.Year == 1994
    assert time.Month == 8
    assert time.Day == 7
    assert time.Hour == 16
    assert time.Minute == 35
    assert time.Second == 0

    time_with_seconds_added = time.AddSeconds(61.87)

    ticks_with_seconds_added_windows = 629118741618700000
    # The tick value does not come out right on Linux. Missing one tick.
    ticks_with_seconds_added_linux = 629118741618700000 - 1

    platform_system = platform.system()
    if platform_system == "Windows":
        assert time_with_seconds_added.Ticks == ticks_with_seconds_added_windows
    elif platform_system == "Linux":
        assert time_with_seconds_added.Ticks == ticks_with_seconds_added_linux
