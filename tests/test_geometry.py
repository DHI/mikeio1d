import pytest

import shapely

from mikeio1d.result_network.geometry import geometry_from_node
from mikeio1d.result_network.geometry import geometry_from_reach
from mikeio1d.result_network.geometry import geometry_from_reaches
from mikeio1d.result_network.geometry import geometry_from_catchment


def test_geometry_from_node(node):
    node = node._node  # dotnet node
    g = geometry_from_node(node)
    assert isinstance(g, shapely.Point)
    assert g.x == pytest.approx(-687934.6000976562)
    assert g.y == pytest.approx(-1056500.69921875)


def test_geometry_from_reach(reach):
    reach = reach.reaches[0]  # dotnet reach
    g = geometry_from_reach(reach)
    assert isinstance(g, shapely.LineString)
    x, y = g.xy
    assert x == pytest.approx([-687887.6008911133, -687907.999206543])
    assert y == pytest.approx([-1056368.9006958008, -1056412.0])
    assert g.length == pytest.approx(47.6827148432828)


def test_geometry_from_reaches(river_reach):
    reach = river_reach
    g = geometry_from_reaches(reach.reaches)
    assert isinstance(g, shapely.LineString)
    # from MIKE+ chainage_points
    expected_coords = {
        53100: (385711.47339682, 5716561.25558023),
        54809.23: (386779.521238822, 5715252.98133197),
        54811.75: (386781.208762897, 5715251.10743646),
        55124.23: (386997.40643911, 5715025.5383054),
    }
    for chainage, expected_coord in expected_coords.items():
        distance = chainage - 53100
        assert g.interpolate(distance).coords[0] == pytest.approx(expected_coord)

    # TODO: not sure why this fails
    #       - the length calculation seems to be different for mike1d and geopandas
    #       - I suspect it's the difference between cartographic vs ellipsoidal distance
    #       - MIKE+ may have mapping from digipoints to chainage
    expected_length = 55124.23 - 53100
    assert expected_length == pytest.approx(g.length)


def test_geometry_from_catchment(catchment):
    catchment = catchment._catchment  # dotnet catchment
    g = geometry_from_catchment(catchment)
    assert isinstance(g, shapely.Polygon)
    assert (g.centroid.x, g.centroid.y) == pytest.approx(
        (catchment.CenterPoint.X, catchment.CenterPoint.Y)
    )
    # TODO: not sure why this fails
    #   - is it because catchment.Area can deviate from the shape area?
    assert g.area == pytest.approx(catchment.Area)


def test_geometry_from_node_runs(many_nodes):
    for node in many_nodes:
        g = geometry_from_node(node._node)
        assert isinstance(g, shapely.Point)


def test_geometry_from_reaches_runs(many_reaches):
    for reach in many_reaches:
        g = geometry_from_reaches(reach.reaches)
        assert isinstance(g, shapely.LineString)


def test_geometry_from_catchments_runs(many_catchments):
    for catchment in many_catchments:
        g = geometry_from_catchment(catchment._catchment)
        assert isinstance(g, shapely.Polygon)
