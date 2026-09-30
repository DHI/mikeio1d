import os
import pytest
from pathlib import Path

import mikeio1d
from mikeio1d import Res1D
from mikeio1d.result_network.various import make_proper_variable_name


@pytest.fixture
def test_file_path():
    test_folder_path = os.path.dirname(os.path.abspath(__file__))
    # Original file name was Exam6Base.res1d
    return os.path.join(test_folder_path, "testdata", "network_chinese.res1d")


@pytest.fixture
def test_file_path_res11():
    test_folder_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(test_folder_path, "testdata", "network_cali.res11")


@pytest.fixture
def test_file_path2():
    test_folder_path = os.path.dirname(os.path.abspath(__file__))
    # Original file name was Exam6Base.res1d
    return os.path.join(test_folder_path, "testdata", "network.res1d")


@pytest.fixture
def test_file_path3():
    test_folder_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(test_folder_path, "testdata", "network_sirius_h2s.res1d")


def test_make_proper_variable_name():
    mpvn = make_proper_variable_name  # alias
    assert mpvn("a") == "a"
    assert mpvn("1") == "_1"
    assert mpvn("1a") == "_1a"
    assert mpvn("a1") == "a1"
    assert mpvn("a1a") == "a1a"
    assert mpvn("myname??++") == "myname"
    assert mpvn("myname??++something") == "myname_something"
    assert mpvn("你好") == "你好"
    assert mpvn("123你好") == "_123你好"


def test_network_attributes_allow_chinese_characters(test_file_path):
    """Test that network attributes allow chinese characters."""
    res = Res1D(test_file_path)
    assert res.nodes.风景
    assert res.nodes.电脑
    assert res.nodes.餐厅
    assert res.nodes.爱情
    assert res.nodes.音乐
    assert res.nodes.星期
    assert res.nodes.医生
    assert res.nodes.美丽
    assert res.nodes.学生
    assert res.nodes.蛋糕


def test_mikeio1d_and_mikepluspy_coexistence(test_file_path):
    # This test cannot run on a GitHub pipeline, because currently there is no way
    # to have MIKE+ installation on a virtual machine there.

    import subprocess

    test_folder_path = os.path.dirname(os.path.abspath(__file__))
    script_path = os.path.join(test_folder_path, "call_mikepluspy_mikeio1d.py")
    exit_code = subprocess.call(["python", script_path, test_file_path])
    assert exit_code == 0


@pytest.mark.parametrize("with_pathlib", [False, True])
def test_res11_to_res1d_conversion(test_file_path_res11, with_pathlib: bool):
    test_file_path_res11 = Path(test_file_path_res11)
    test_file_path_res1d = test_file_path_res11.with_suffix(".res1d")

    if not with_pathlib:
        test_file_path_res11 = str(test_file_path_res11)
        test_file_path_res1d = str(test_file_path_res1d)

    res11 = Res1D(test_file_path_res11)
    res11.read()
    res11.save(test_file_path_res1d)

    res1d = Res1D(test_file_path_res1d)

    df_res11 = res11.read()
    df_res1d = res1d.read()

    assert df_res11.max().max() == df_res1d.max().max()


def test_saving_with_filter(test_file_path2):
    res_unfiltered = mikeio1d.open(test_file_path2)
    assert res_unfiltered.quantities == ["WaterLevel", "Discharge"]

    res_filtered = mikeio1d.open(test_file_path2, quantities=["WaterLevel"])
    res_filtered.save("filtered.res1d")

    res_filtered = mikeio1d.open("filtered.res1d")
    assert res_filtered.quantities == ["WaterLevel"]

    os.remove("filtered.res1d")


def test_saving_with_filter_for_not_predefined_quantities(test_file_path3):
    res_unfiltered = mikeio1d.open(test_file_path3)
    assert res_unfiltered.quantities == ["S_II", "S_O"]

    res_filtered = mikeio1d.open(test_file_path3, quantities=["S_II"])
    test_file_path3_filtered = test_file_path3.replace(".res1d", "_filtered.res1d")
    res_filtered.save(test_file_path3_filtered)

    res_filtered = mikeio1d.open(test_file_path3_filtered)
    assert res_filtered.quantities == ["S_II"]

    os.remove(test_file_path3_filtered)
