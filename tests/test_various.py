import os
import pytest

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


def test_res11_to_res1d_conversion(test_file_path_res11):
    res11 = Res1D(test_file_path_res11)

    test_file_path_res1d = test_file_path_res11.replace("res11", "res1d")
    res11.save(test_file_path_res1d)

    res1d = Res1D(test_file_path_res1d)

    df_res11 = res11.read()
    df_res1d = res1d.read()

    assert df_res11.max().max() == df_res1d.max().max()
