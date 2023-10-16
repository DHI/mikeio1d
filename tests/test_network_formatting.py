"""
Tests for the formatting of the result network objects."""


def test_location_str_repr_header_line(node, reach, catchment):
    assert node.__repr__().startswith(
        "<ResultNode>"
    ), "Node header line is not correct."
    assert reach.__repr__().startswith(
        "<ResultReach>"
    ), "Reach header line is not correct."
    assert catchment.__repr__().startswith(
        "<ResultCatchment>"
    ), "Catchment header line is not correct."


def test_location_html_repr_header_line(node, reach, catchment):
    assert node._repr_html_().startswith(
        "&lt;ResultNode&gt;"
    ), "Node header line is not correct."
    assert reach._repr_html_().startswith(
        "&lt;ResultReach&gt;"
    ), "Reach header line is not correct."
    assert catchment._repr_html_().startswith(
        "&lt;ResultCatchment&gt;"
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
    expected_html_repr = """&lt;ResultNode&gt;
    <style>
        ul {
            margin: 0px;
            padding: 0px;
            padding-left: 2em;
        }
    </style>
    <details><summary>Attributes</summary><ul><li>type: Manhole</li><li>id: 1</li><li>xcoord: -687934.6000976562</li><li>ycoord: -1056500.69921875</li><li>ground_level: 197.07000732421875</li><li>bottom_level: 195.0500030517578</li><li>critical_level: inf</li><li>diameter: 1.0</li></ul></details><details><summary>Quantities</summary><ul><li>WaterLevel</li></ul></details>"""
    assert html_repr == expected_html_repr


def test_single_catchment_html_repr(catchment):
    html_repr = catchment._repr_html_()
    expected_html_repr = """&lt;ResultCatchment&gt;
    <style>
        ul {
            margin: 0px;
            padding: 0px;
            padding-left: 2em;
        }
    </style>
    <details><summary>Attributes</summary><ul><li>id: 100_16_16</li><li>area: 22800.0</li><li>center_xcoord: -687904.1384546768</li><li>center_ycoord: -1056368.7400316757</li></ul></details><details><summary>Quantities</summary><ul><li>TotalRunOff</li><li>ActualRainfall</li><li>ZinkLoadRR</li><li>ZinkMassAccumulatedRR</li><li>ZinkRR</li></ul></details>"""
    assert html_repr == expected_html_repr
