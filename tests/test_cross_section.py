import pytest

from typing import List
from contextlib import nullcontext

import numpy as np
import pandas as pd

from mikeio1d import Xns11

from mikeio1d.cross_sections import CrossSection
from mikeio1d.cross_sections import ResistanceType
from mikeio1d.cross_sections import ResistanceDistribution

from tests import testdata


def create_xz_data():
    x = np.arange(0, 101, 10).astype(float)
    z = 10 + ((x - 50) ** 2) / 250
    return x, z


@pytest.fixture
def xz_data():
    return create_xz_data()


@pytest.fixture
def xns_basic():
    return Xns11(testdata.xsections_xns11)


@pytest.fixture
def cs_dummy(xz_data) -> CrossSection:
    x, z = xz_data
    return CrossSection.from_xz(
        x=x, z=z, location_id="my_location", chainage=100, topo_id="my_topo"
    )


@pytest.fixture
def cs_basic(xns_basic) -> CrossSection:
    return xns_basic.xsections.values()[0]


@pytest.fixture
def cs_sample(xns_basic) -> List[CrossSection]:
    x = list(xns_basic.xsections.values())
    x = x[::2]
    return x


class TestCrossSectionCreation:
    def test_create_cross_section(self, xz_data):
        x, z = xz_data
        cs = CrossSection.from_xz(
            x=x, z=z, location_id="my_location", chainage=100, topo_id="my_topo"
        )
        assert isinstance(cs, CrossSection)

    def test_topo_id(self, cs_dummy):
        assert cs_dummy.topo_id == "my_topo"

    def test_location_id(self, cs_dummy):
        assert cs_dummy.location_id == "my_location"

    def test_chainage(self, cs_dummy):
        assert cs_dummy.chainage == 100

    def test_bottom_level(self, cs_dummy):
        assert cs_dummy.bottom_level == 10

    def test_height(self, cs_dummy):
        assert cs_dummy.height == 10

    def test_interpolate(self, cs_dummy):
        assert cs_dummy.interpolated is False

    def test_is_open(self, cs_dummy):
        assert cs_dummy.is_open is True

    def test_max_width(self, cs_dummy):
        assert cs_dummy.max_width == 100

    def test_min_water_depth(self, cs_dummy):
        assert cs_dummy.min_water_depth == 0

    def test_zmax(self, cs_dummy):
        assert cs_dummy.zmax == 20

    def test_zmin(self, cs_dummy):
        assert cs_dummy.zmin == 10

    @pytest.mark.skip
    def test_geometry(self, cs_dummy):
        # TODO
        assert False

    def test_resistance_type_get(self, cs_dummy):
        assert cs_dummy.resistance_type == ResistanceType.RELATIVE

    def test_resistance_type_set(self, cs_dummy):
        cs_dummy.resistance_type = ResistanceType.MANNINGS_N
        assert cs_dummy.resistance_type == ResistanceType.MANNINGS_N

    def test_resistance_distribution_get(self, cs_dummy):
        assert cs_dummy.resistance_distribution == ResistanceDistribution.UNIFORM

    def test_resistance_distribution_set(self, cs_dummy):
        cs_dummy.resistance_distribution = ResistanceDistribution.ZONES
        assert cs_dummy.resistance_distribution == ResistanceDistribution.ZONES

    @pytest.mark.parametrize(
        "zone", ["resistance_left_high_flow", "resistance_right_high_flow", "resistance_low_flow"]
    )
    @pytest.mark.parametrize("get_or_set", ["get", "set"])
    def test_resistance_zones_warning(self, cs_sample, zone, get_or_set):
        """
        Warns when using zone related resistances with non-zone resistance distribution
        """
        tested_one_zone_cross_section = False
        for cs in cs_sample:
            should_warn = cs.resistance_distribution != ResistanceDistribution.ZONES
            tested_one_zone_cross_section = tested_one_zone_cross_section or not should_warn
            with pytest.warns() if should_warn else nullcontext():
                if get_or_set == "get":
                    getattr(cs, zone)
                else:
                    setattr(cs, zone, 2.0)

        assert tested_one_zone_cross_section is True

    @pytest.mark.parametrize(
        "zone", ["resistance_left_high_flow", "resistance_right_high_flow", "resistance_low_flow"]
    )
    def test_resistance_zones_get(self, cs_dummy, zone):
        cs_dummy.resistance_distribution = ResistanceDistribution.ZONES
        assert getattr(cs_dummy, zone) == 1.0

    @pytest.mark.parametrize(
        "zone", ["resistance_left_high_flow", "resistance_right_high_flow", "resistance_low_flow"]
    )
    def test_resistance_zones_set(self, cs_dummy, zone):
        cs_dummy.resistance_distribution = ResistanceDistribution.ZONES
        setattr(cs_dummy, zone, 2.0)
        assert getattr(cs_dummy, zone) == 2.0

    def test_number_of_processing_levels_get(self, cs_dummy):
        DEFAULT_PROCESSING_LEVELS = 20
        assert cs_dummy.number_of_processing_levels == DEFAULT_PROCESSING_LEVELS

        cs_dummy.processing_levels = cs_dummy.processing_levels[:10]
        assert cs_dummy.number_of_processing_levels == len(cs_dummy.processing_levels)

    def test_number_of_processing_levels_set(self, cs_dummy):
        cs_dummy.number_of_processing_levels = 10
        assert cs_dummy.number_of_processing_levels == 10

        cs_dummy.processing_levels = cs_dummy.processing_levels[:5]
        cs_dummy.number_of_processing_levels = 10
        assert cs_dummy.number_of_processing_levels == 10

    def test_processed_allow_recompute_get(self, cs_dummy):
        DEFAULT_ALLOW_RECOMPUTE = True
        assert cs_dummy.processed_allow_recompute is DEFAULT_ALLOW_RECOMPUTE

    def test_processed_allow_recompute_set(self, cs_dummy):
        cs_dummy.processed_allow_recompute = False
        assert cs_dummy.processed_allow_recompute is False

    def test_processed_allow_recompute_false_functionality(self, cs_dummy):
        # TODO
        return True

    def test_calculate_conveyance_factor(self, cs_dummy):
        df = cs_dummy.processed
        resistance, flow_area, radius = df.resistance, df.flow_area, df.radius
        conveyances = tuple(
            r * A * R ** (2.0 / 3) for r, A, R in zip(resistance, flow_area, radius)
        )
        np.testing.assert_array_equal(conveyances, df.conveyance_factor)

    def test_processed_get(self, cs_sample):
        for cs in cs_sample:
            df = cs.processed
            assert isinstance(df, pd.DataFrame)
            assert len(df) == cs.number_of_processing_levels, cs
            expected_columns = {
                "level",
                "flow_area",
                "radius",
                "storage_width",
                "additional_storage_area",
                "resistance",
                "conveyance_factor",
            }
            set(df.columns) == expected_columns
            base_xs = cs._m1d_cross_section.BaseCrossSection
            expected_vs_actual = [
                (np.array(base_xs.ProcessedLevels), df.level),
                (np.array(base_xs.ProcessedFlowAreas), df.flow_area),
                (np.array(base_xs.ProcessedRadii), df.radius),
                (np.array(base_xs.ProcessedStorageWidths), df.storage_width),
                (np.array(base_xs.ProcessedAdditionalSurfaceAreas), df.additional_storage_area),
                (np.array(base_xs.ProcessedResistanceFactors), df.resistance),
            ]
            expected_conveyance = cs._calculate_conveyance_factor(
                df.resistance, df.flow_area, df.radius
            )
            expected_vs_actual.append((expected_conveyance, df.conveyance_factor))

            for expected, actual in expected_vs_actual:
                np.testing.assert_array_equal(expected, actual)
