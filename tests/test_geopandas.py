import pytest

pytest.importorskip("geopandas")

from geopandas import GeoDataFrame  # noqa: E402
from pyproj import CRS  # noqa: E402
from shapely import Point  # noqa: E402
from shapely import LineString  # noqa: E402
from shapely import Polygon  # noqa: E402

from mikeio1d.geometry.geopandas import GeoPandasReachesConverter  # noqa: E402
from mikeio1d.geometry.geopandas import GeoPandasReachesConverterSegmented  # noqa: E402
from mikeio1d.geometry.geopandas import GeoPandasCatchmentsConverter  # noqa: E402
from mikeio1d.geometry.geopandas import GeoPandasNodesConverter  # noqa: E402

from mikeio1d.geometry import ReachGeometry  # noqa: E402

from mikeio1d.quantities import TimeSeriesId  # noqa: E402


def test_nodes_to_geopandas_basic(res1d_network):
    """Test that nodes.to_geopandas() returns a GeoDataFrame."""
    gdf = res1d_network.result_network.nodes.to_geopandas()
    assert isinstance(gdf, GeoDataFrame)
    assert len(gdf) == len(res1d_network.result_network.nodes)
    assert all(isinstance(x, Point) for x in gdf.geometry)


def test_nodes_to_geopandas_with_quantities_basic(res1d_river_network):
    """Test that nodes.to_geopandas() returns a GeoDataFrame with quantities."""
    gdf = res1d_river_network.result_network.nodes.to_geopandas("max")
    assert isinstance(gdf, GeoDataFrame)
    assert "max_WaterLevel" in gdf.columns


def test_reaches_to_geopandas_basic(res1d_network):
    """Test that reaches.to_geopandas() returns a GeoDataFrame."""
    gdf = res1d_network.result_network.reaches.to_geopandas()
    assert isinstance(gdf, GeoDataFrame)
    assert len(gdf) == len(res1d_network.result_network.reaches)
    assert all(isinstance(x, LineString) for x in gdf.geometry)


@pytest.mark.parametrize("segmented", [True, False])
def test_reaches_to_geopandas_with_quantities_basic(res1d_river_network, segmented):
    """Test that reaches.to_geopandas() returns a GeoDataFrame with quantities."""
    gdf = res1d_river_network.result_network.reaches.to_geopandas("max", segmented=segmented)
    assert isinstance(gdf, GeoDataFrame)
    assert "max_Discharge" in gdf.columns


def test_catchments_to_geopandas_basic(res1d_network):
    """Test that catchments.to_geopandas() returns a GeoDataFrame."""
    gdf = res1d_network.result_network.catchments.to_geopandas()
    assert isinstance(gdf, GeoDataFrame)
    assert len(gdf) == len(res1d_network.result_network.catchments)
    assert all(isinstance(x, Polygon) for x in gdf.geometry)


def test_catchments_to_geopandas_with_quantities_basic(res1d_catchments):
    """Test that catchments.to_geopandas() returns a GeoDataFrame with quantities."""
    gdf = res1d_catchments.catchments.to_geopandas("max")
    assert isinstance(gdf, GeoDataFrame)
    assert "max_TotalRunOff" in gdf.columns


def test_network_to_geopandas_basic(res1d_network):
    """Test that network.to_geopandas() returns a GeoDataFrame."""
    gdf = res1d_network.result_network.to_geopandas()
    assert isinstance(gdf, GeoDataFrame)
    assert len(gdf) == len(res1d_network.result_network.nodes) + len(
        res1d_network.result_network.reaches
    ) + len(res1d_network.result_network.catchments)
    assert all(isinstance(x, (Point, LineString, Polygon)) for x in gdf.geometry)


def test_network_to_geopandas_with_quantities(res1d_network):
    """Test that network.to_geopandas() raises error if attempts to use agg."""
    with pytest.raises(TypeError):
        res1d_network.result_network.to_geopandas("max")


def test_network_to_geopandas_crs(res1d_river_network):
    """Test that network.to_geopandas() returns a GeoDataFrame with the correct CRS."""
    gdf = res1d_river_network.result_network.to_geopandas()
    assert isinstance(gdf.crs, CRS)
    assert gdf.crs.to_epsg() == 25832


def test_geopandas_reaches_converter(res1d_river_network):
    """Test GeoPandasReachesConverter."""
    converter = GeoPandasReachesConverter()
    gdf = converter.to_geopandas(res1d_river_network.reaches)
    assert isinstance(gdf, GeoDataFrame)
    assert len(gdf) == len(res1d_river_network.reaches)
    assert ["group", "name", "geometry"] == list(gdf.columns)
    sample_row = gdf.iloc[2]
    name, geometry = sample_row["name"], sample_row["geometry"]
    assert res1d_river_network.reaches[name].geometry.to_shapely() == geometry


def test_geopandas_reaches_converter_segmented(res1d_river_network):
    """Test GeoPandasReachesConverterSegmented."""
    converter = GeoPandasReachesConverterSegmented()
    gdf = converter.to_geopandas(res1d_river_network.reaches)
    assert isinstance(gdf, GeoDataFrame)
    number_of_segments = sum(len(reach.reaches) for reach in res1d_river_network.reaches.values())
    assert len(gdf) == number_of_segments
    assert ["group", "name", "tag", "geometry"] == list(gdf.columns)
    sample_reach_name = "river"
    sample_reach_segments = res1d_river_network.reaches[sample_reach_name].reaches
    sample_reach = sample_reach_segments[len(sample_reach_segments) // 2]
    sample_reach_tag = TimeSeriesId.create_reach_span_tag(sample_reach)
    geometry = gdf.query(f"name == '{sample_reach_name}' and tag == '{sample_reach_tag}'").iloc[0][
        "geometry"
    ]
    expected_geometry = ReachGeometry.from_m1d_reaches(sample_reach).to_shapely()
    assert expected_geometry == geometry


def test_geopandas_catchments_converter(res1d_catchments):
    """Test GeoPandasCatchmentsConverter."""
    converter = GeoPandasCatchmentsConverter()
    gdf = converter.to_geopandas(res1d_catchments.catchments)
    assert isinstance(gdf, GeoDataFrame)
    assert len(gdf) == len(res1d_catchments.catchments)
    assert ["group", "name", "geometry"] == list(gdf.columns)
    sample_row = gdf.iloc[2]
    name, geometry = sample_row["name"], sample_row["geometry"]
    assert res1d_catchments.catchments[name].geometry.to_shapely() == geometry


def test_geopandas_nodes_converter(res1d_network):
    """Test GeoPandasNodesConverter."""
    converter = GeoPandasNodesConverter()
    gdf = converter.to_geopandas(res1d_network.nodes)
    assert isinstance(gdf, GeoDataFrame)
    assert len(gdf) == len(res1d_network.nodes)
    assert ["group", "name", "geometry"] == list(gdf.columns)
    sample_row = gdf.iloc[2]
    name, geometry = sample_row["name"], sample_row["geometry"]
    assert res1d_network.nodes[name].geometry.to_shapely() == geometry
