import pytest

from geopandas import GeoDataFrame
from pyproj import CRS
from shapely import Point
from shapely import LineString
from shapely import Polygon


def test_nodes_to_geopandas_basic(res1d_network):
    """Test that nodes.to_geopandas() returns a GeoDataFrame."""
    gdf = res1d_network.result_network.nodes.to_geopandas()
    assert isinstance(gdf, GeoDataFrame)
    assert len(gdf) == len(res1d_network.result_network.nodes)
    assert all(isinstance(x, Point) for x in gdf.geometry)


def test_reaches_to_geopandas_basic(res1d_network):
    """Test that reaches.to_geopandas() returns a GeoDataFrame."""
    gdf = res1d_network.result_network.reaches.to_geopandas()
    assert isinstance(gdf, GeoDataFrame)
    assert len(gdf) == len(res1d_network.result_network.reaches)
    assert all(isinstance(x, LineString) for x in gdf.geometry)


def test_catchments_to_geopandas_basic(res1d_network):
    """Test that catchments.to_geopandas() returns a GeoDataFrame."""
    gdf = res1d_network.result_network.catchments.to_geopandas()
    assert isinstance(gdf, GeoDataFrame)
    assert len(gdf) == len(res1d_network.result_network.catchments)
    assert all(isinstance(x, Polygon) for x in gdf.geometry)


def test_network_to_geopandas_basic(res1d_network):
    """Test that network.to_geopandas() returns a GeoDataFrame."""
    gdf = res1d_network.result_network.to_geopandas()
    assert isinstance(gdf, GeoDataFrame)
    assert len(gdf) == len(res1d_network.result_network.nodes) + len(
        res1d_network.result_network.reaches
    ) + len(res1d_network.result_network.catchments)
    assert all(isinstance(x, (Point, LineString, Polygon)) for x in gdf.geometry)


def test_network_to_geopandas_crs(res1d_river_network):
    """Test that network.to_geopandas() returns a GeoDataFrame with the correct CRS."""
    gdf = res1d_river_network.result_network.to_geopandas()
    assert isinstance(gdf.crs, CRS)
    assert gdf.crs.to_epsg() == 25832


# TODO: test import of mikeio1d does not break if geopandas isn't installed
