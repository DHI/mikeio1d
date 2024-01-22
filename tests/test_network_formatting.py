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
    </style>
    <details><summary>Attributes (8)</summary><ul><li>id: 1</li><li>type: Manhole</li><li>xcoord: -687934.6000976562</li><li>ycoord: -1056500.69921875</li><li>ground_level: 197.07000732421875</li><li>bottom_level: 195.0500030517578</li><li>critical_level: inf</li><li>diameter: 1.0</li></ul></details><details><summary>Quantities (1)</summary><ul><li>WaterLevel</li></ul></details>"""
    assert html_repr == expected_html_repr


def test_single_catchment_html_repr(catchment):
    html_repr = catchment._repr_html_()
    expected_html_repr = """&lt;Catchment: 100_16_16&gt;
    <style>
        ul {
            margin: 0px;
            padding: 0px;
            padding-left: 2em;
        }
    </style>
    <details><summary>Attributes (3)</summary><ul><li>id: 100_16_16</li><li>area: 22800.0</li><li>type: Kinematic Wave</li></ul></details><details><summary>Quantities (5)</summary><ul><li>TotalRunOff</li><li>ActualRainfall</li><li>ZinkLoadRR</li><li>ZinkMassAccumulatedRR</li><li>ZinkRR</li></ul></details>"""
    assert html_repr == expected_html_repr


def test_single_reach_html_repr(river_reach):
    html_repr = river_reach._repr_html_()
    expected_html_repr = """&lt;Reach: river&gt;
    <style>
        ul {
            margin: 0px;
            padding: 0px;
            padding-left: 2em;
        }
    </style>
    <details><summary>Attributes (5)</summary><ul><li>name: river</li><li>length: 2024.2276598819008</li><li>start_chainage: 53100.0</li><li>end_chainage: 55124.2276598819</li><li>n_gridpoints: 94</li></ul></details><details><summary>Quantities (4)</summary><ul><li>WaterLevel</li><li>ManningResistanceNumber</li><li>Discharge</li><li>FlowVelocity</li></ul></details>"""
    assert html_repr == expected_html_repr


def test_single_structure_html_repr(structure):
    html_repr = structure._repr_html_()
    expected_html_repr = """&lt;Weir: 119w1&gt;
    <style>
        ul {
            margin: 0px;
            padding: 0px;
            padding-left: 2em;
        }
    </style>
    <details><summary>Attributes (3)</summary><ul><li>id: 119w1</li><li>type: Weir</li><li>chainage: 0.5</li></ul></details><details><summary>Quantities (1)</summary><ul><li>Discharge</li></ul></details>"""
    assert html_repr == expected_html_repr
