import pytest

import numpy as np

from mikeio1d.cross_sections import CrossSection


def create_xz_data():
    x = np.arange(0, 101, 10).astype(float)
    z = 10 + ((x - 50) ** 2) / 250
    return x, z


@pytest.fixture
def xz_data():
    return create_xz_data()


class TestCrossSectionCreation:
    def test_create_cross_section(self, xz_data):
        x, z = xz_data
        cs = CrossSection.from_xz(
            x=x, z=z, location_id="my_location", chainage=100, topo_id="my_topo"
        )
        assert isinstance(cs, CrossSection)
        assert cs.location_id == "my_location"
        assert pytest.approx(cs.chainage) == 100
        assert cs.topo_id == "my_topo"
