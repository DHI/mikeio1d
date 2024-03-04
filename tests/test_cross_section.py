import pytest

import numpy as np

from mikeio1d.cross_sections import CrossSection
from mikeio1d.cross_sections import ResistanceType
from mikeio1d.cross_sections import ResistanceDistribution


def create_xz_data():
    x = np.arange(0, 101, 10).astype(float)
    z = 10 + ((x - 50) ** 2) / 250
    return x, z


@pytest.fixture
def xz_data():
    return create_xz_data()


@pytest.fixture
def dummy_cs(xz_data):
    x, z = xz_data
    return CrossSection.from_xz(
        x=x, z=z, location_id="my_location", chainage=100, topo_id="my_topo"
    )


class TestCrossSectionCreation:
    def test_create_cross_section(self, xz_data):
        x, z = xz_data
        cs = CrossSection.from_xz(
            x=x, z=z, location_id="my_location", chainage=100, topo_id="my_topo"
        )
        assert isinstance(cs, CrossSection)

    def test_topo_id(self, dummy_cs):
        assert dummy_cs.topo_id == "my_topo"

    def test_location_id(self, dummy_cs):
        assert dummy_cs.location_id == "my_location"

    def test_chainage(self, dummy_cs):
        assert dummy_cs.chainage == 100

    def test_bottom_level(self, dummy_cs):
        assert dummy_cs.bottom_level == 10

    def test_height(self, dummy_cs):
        assert dummy_cs.height == 10

    def test_interpolate(self, dummy_cs):
        assert dummy_cs.interpolated is False

    def test_is_open(self, dummy_cs):
        assert dummy_cs.is_open is True

    def test_max_width(self, dummy_cs):
        assert dummy_cs.max_width == 100

    def test_min_water_depth(self, dummy_cs):
        assert dummy_cs.min_water_depth == 0

    def test_zmax(self, dummy_cs):
        assert dummy_cs.zmax == 20

    def test_zmin(self, dummy_cs):
        assert dummy_cs.zmin == 10

    def test_geometry(self, dummy_cs):
        # TODO
        assert False

    def test_resistance_type_get(self, dummy_cs):
        assert dummy_cs.resistance_type == ResistanceType.RELATIVE

    def test_resistance_type_set(self, dummy_cs):
        dummy_cs.resistance_type = ResistanceType.MANNINGS_N
        assert dummy_cs.resistance_type == ResistanceType.MANNINGS_N

    def test_resistance_distribution_get(self, dummy_cs):
        assert dummy_cs.resistance_distribution == ResistanceDistribution.UNIFORM

    def test_resistance_distribution_set(self, dummy_cs):
        dummy_cs.resistance_distribution = ResistanceDistribution.ZONES
        assert dummy_cs.resistance_distribution == ResistanceDistribution.ZONES
