from mikeio1d.result_network.various import make_proper_variable_name


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
