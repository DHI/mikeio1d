"""
Tests for the formatting of the result network objects."""


def test_location_str_repr_header_line(node, reach, catchment, structure):
    assert node.__repr__().startswith("<Manhole: 1>"), "Node header line is not correct."
    assert reach.__repr__().startswith("<Reach: 100l1>"), "Reach header line is not correct."
    assert catchment.__repr__().startswith(
        "<Catchment: 100_16_16>"
    ), "Catchment header line is not correct."
    assert structure.__repr__().startswith("<Weir: 119w1>"), "Structure header line is not correct."


def test_location_html_repr_header_line(node, reach, catchment):
    assert node._repr_html_().startswith("&lt;Manhole: 1&gt;"), "Node header line is not correct."
    assert reach._repr_html_().startswith(
        "&lt;Reach: 100l1&gt;"
    ), "Reach header line is not correct."
    assert catchment._repr_html_().startswith(
        "&lt;Catchment: 100_16_16&gt;"
    ), "Catchment header line is not correct."


def test_node_html_repr_runs(many_nodes):
    for node in many_nodes:
        node._repr_html_()


def test_reach_html_repr_runs(many_reaches):
    for reach in many_reaches:
        reach._repr_html_()


def test_catchment_html_repr_runs(many_catchments):
    for catchment in many_catchments:
        catchment._repr_html_()


def test_single_node_html_repr(node):
    html_repr = node._repr_html_()
    expected_html_repr = """&lt;Manhole: 1&gt;
    <style>
        ul {
            margin: 0px;
            padding: 0px;
            padding-left: 2em;
        }
    </style>"""
    assert expected_html_repr in html_repr


def test_single_catchment_html_repr(catchment):
    html_repr = catchment._repr_html_()
    expected_html_repr = """&lt;Catchment: 100_16_16&gt;
    <style>
        ul {
            margin: 0px;
            padding: 0px;
            padding-left: 2em;
        }
    </style>"""
    assert expected_html_repr in html_repr


def test_single_reach_html_repr(river_reach):
    html_repr = river_reach._repr_html_()
    expected_html_repr = """&lt;Reach: river&gt;
    <style>
        ul {
            margin: 0px;
            padding: 0px;
            padding-left: 2em;
        }
    </style>"""
    assert expected_html_repr in html_repr


def test_single_structure_html_repr(structure):
    html_repr = structure._repr_html_()
    expected_html_repr = """&lt;Weir: 119w1&gt;
    <style>
        ul {
            margin: 0px;
            padding: 0px;
            padding-left: 2em;
        }
    </style>"""
    assert expected_html_repr in html_repr
