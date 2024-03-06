import pytest

from typing import List
from contextlib import nullcontext

import numpy as np
import pandas as pd

from mikeio1d import Xns11

from mikeio1d.cross_sections import CrossSection
from mikeio1d.cross_sections import ResistanceType
from mikeio1d.cross_sections import ResistanceDistribution
from mikeio1d.cross_sections import RadiusType
from mikeio1d.cross_sections import ProcessLevelsMethod
from mikeio1d.cross_sections import Marker

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
    return list(xns_basic.xsections.values())[0]


@pytest.fixture
def cs_sample(xns_basic) -> List[CrossSection]:
    x = list(xns_basic.xsections.values())
    x = x[::2]
    return x


class TestCrossSectionUnits:
    """
    Unit tests for the CrossSection class.
    """

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

    def test_coords_get(self, cs_basic):
        coords = cs_basic.coords
        assert len(coords) == 2
        assert len(coords[0]) == 2
        assert coords[0][0] == 938162.512
        assert coords[0][1] == 377327.367
        assert coords[1][0] == 938163.08
        assert coords[1][1] == 377291.372

    def test_geometry(self, cs_basic):
        pytest.importorskip("shapely")
        from mikeio1d.geometry import CrossSectionGeometry

        geometry = cs_basic.geometry
        assert isinstance(geometry, CrossSectionGeometry)
        np.testing.assert_array_equal(geometry.coords, cs_basic.coords)

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

    def test_radius_type(self, cs_dummy):
        assert cs_dummy.radius_type == RadiusType.RESISTANCE_RADIUS

    def test_radius_type_set(self, cs_dummy):
        cs_dummy.radius_type = RadiusType.HYDRAULIC_RADIUS_TOTAL_AREA
        assert cs_dummy.radius_type == RadiusType.HYDRAULIC_RADIUS_TOTAL_AREA

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

    def test_processing_levels_method_get(self, cs_dummy):
        assert cs_dummy.processing_levels_method == ProcessLevelsMethod.AUTOMATIC_LEVELS

    def test_processing_levels_method_set(self, cs_dummy):
        automatic_levels = cs_dummy.processing_levels

        cs_dummy.processing_levels_method = ProcessLevelsMethod.EQUIDISTANT_LEVELS
        assert cs_dummy.processing_levels_method == ProcessLevelsMethod.EQUIDISTANT_LEVELS

        equidistant_levels = cs_dummy.processing_levels
        assert automatic_levels != equidistant_levels

        cs_dummy.processing_levels_method = ProcessLevelsMethod.USER_DEFINED_LEVELS
        assert cs_dummy.processing_levels_method == ProcessLevelsMethod.USER_DEFINED_LEVELS

    def test_processing_levels_get(self, cs_dummy):
        DEFAULT_PROCESSING_LEVELS = 20
        assert len(cs_dummy.processing_levels) == DEFAULT_PROCESSING_LEVELS
        assert min(cs_dummy.processing_levels) == cs_dummy.zmin
        assert max(cs_dummy.processing_levels) == cs_dummy.zmax

    def test_processing_levels_set(self, cs_dummy):
        cs_dummy.processing_levels = [10, 15, 20]
        assert len(cs_dummy.processing_levels) == 3

    def test_processed_allow_recompute_get(self, cs_dummy):
        DEFAULT_ALLOW_RECOMPUTE = True
        assert cs_dummy.processed_allow_recompute is DEFAULT_ALLOW_RECOMPUTE

    def test_processed_allow_recompute_set(self, cs_dummy):
        cs_dummy.processed_allow_recompute = False
        assert cs_dummy.processed_allow_recompute is False

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

    def test_processed_set(self, cs_dummy):
        df = cs_dummy.processed
        df = df.iloc[:5]
        cs_dummy.processed = df
        assert len(cs_dummy.processed) == 5
        df.level = df.level + 1
        cs_dummy.processed = df
        np.testing.assert_array_equal(cs_dummy.processed.level, df.level)
        df.storage_width = df.storage_width * 10
        cs_dummy.processed = df
        np.testing.assert_array_equal(cs_dummy.processed.storage_width, df.storage_width)
        df.flow_area = df.flow_area * 10
        cs_dummy.processed = df
        np.testing.assert_array_equal(cs_dummy.processed.flow_area, df.flow_area)
        df.radius = df.radius * 10
        cs_dummy.processed = df
        np.testing.assert_array_equal(cs_dummy.processed.radius, df.radius)
        df.additional_storage_area = df.additional_storage_area + 100
        cs_dummy.processed = df
        np.testing.assert_array_equal(
            cs_dummy.processed.additional_storage_area, df.additional_storage_area
        )
        df.conveyance_factor = df.conveyance_factor * 1000
        cs_dummy.processed = df
        with pytest.raises(AssertionError):
            np.testing.assert_array_equal(
                cs_dummy.processed.conveyance_factor, df.conveyance_factor
            )

    def test_raw_get(self, cs_dummy, xz_data):
        x, z = xz_data
        df = cs_dummy.raw
        assert isinstance(df, pd.DataFrame)
        expected_columns = {
            "markers",
            "marker_labels",
            "x",
            "z",
            "resistance",
        }
        assert set(df.columns) == expected_columns
        np.testing.assert_array_equal(df.x, x)
        np.testing.assert_array_equal(df.z, z)
        np.testing.assert_array_equal(df.resistance, np.ones_like(x))
        empty_markers = np.array([""] * len(x))
        empty_markers[0] = str(int(Marker.LEFT_LEVEE_BANK))
        empty_markers[-1] = str(int(Marker.RIGHT_LEVEE_BANK))
        empty_markers[df.z.idxmin()] = str(int(Marker.LOWEST_POINT))
        np.testing.assert_array_equal(df.markers, empty_markers)
        empty_marker_labels = np.array(
            [Marker.pretty(int(m)) if m != "" else "" for m in empty_markers]
        )
        np.testing.assert_array_equal(df.marker_labels, empty_marker_labels)

    def test_raw_set(self, cs_dummy):
        df = cs_dummy.raw
        df = df.iloc[3:-3].reset_index(drop=True)
        cs_dummy.raw = df
        pd.testing.assert_frame_equal(cs_dummy.raw, df)

        df.iloc[0, df.columns.get_loc("markers")] = str(Marker.LEFT_LEVEE_BANK.value)
        df.iloc[-1, df.columns.get_loc("markers")] = str(Marker.RIGHT_LEVEE_BANK.value)
        cs_dummy.raw = df
        # This raises an exception since labels are automatically filled in.
        with pytest.raises(Exception):
            pd.testing.assert_frame_equal(cs_dummy.raw, df)

        # If we did include the labels, then no error.
        df.marker_labels = df.markers.apply(lambda m: Marker.pretty(int(m)) if m != "" else "")
        cs_dummy.raw = df
        pd.testing.assert_frame_equal(cs_dummy.raw, df)

        # Set user marker
        df.iloc[0, df.columns.get_loc("markers")] += ",99"
        markers = Marker.list_from_string(df.markers.iloc[0])
        cs_dummy.raw = df
        set_markers = Marker.list_from_string(cs_dummy.raw.markers.iloc[0])
        assert set(set_markers) == set(markers)

        # Raise error if duplicate markers found
        with pytest.raises(ValueError):
            df.iloc[0, df.columns.get_loc("markers")] += f",{int(Marker.LOWEST_POINT)}"
            cs_dummy.raw = df

        df.iloc[0, df.columns.get_loc("markers")] = ""
        df.iloc[1, df.columns.get_loc("markers")] = str(Marker.LEFT_LEVEE_BANK.value)
        cs_dummy.raw = df
        assert cs_dummy.raw.markers.iloc[0] == ""
        assert cs_dummy.raw.markers.iloc[1] == str(Marker.LEFT_LEVEE_BANK.value)

    def test_markers_get(self, cs_dummy):
        markers = cs_dummy.markers
        assert isinstance(markers, pd.DataFrame)
        expected_columns = {
            "marker",
            "marker_label",
            "x",
            "z",
        }
        assert set(markers.columns) == expected_columns
        assert len(markers) == 3
        assert {
            Marker.LEFT_LEVEE_BANK.value,
            Marker.LOWEST_POINT.value,
            Marker.RIGHT_LEVEE_BANK.value,
        } == set(markers.marker)

        df: pd.DataFrame = cs_dummy.raw
        df = df[df.markers != ""]
        df = df[["markers", "marker_labels", "x", "z"]]
        df = df.rename(columns={"markers": "marker", "marker_labels": "marker_label"})
        df = df.explode("marker").reset_index(drop=True)
        df.marker = df.marker.astype(np.int64)
        pd.testing.assert_frame_equal(markers, df), "Markers do not match raw data."

    def test_markers_set(self, cs_dummy):
        markers = cs_dummy.markers
        markers = markers.iloc[[1]]
        cs_dummy.markers = markers
        assert len(cs_dummy.markers) == 1
        assert cs_dummy.markers.iloc[0].marker == Marker.LOWEST_POINT.value
        raw_markers = cs_dummy.raw[cs_dummy.raw.markers != ""]
        assert len(raw_markers) == 1
        assert raw_markers.iloc[0].markers == str(Marker.LOWEST_POINT.value)

    def test_set_marker(self, cs_dummy):
        cs_dummy.set_marker(99, x=25)
        df_markers = cs_dummy.markers
        x = df_markers.loc[df_markers.marker == 99, "x"].values[0]
        z = df_markers.loc[df_markers.marker == 99, "z"].values[0]
        assert x == 20
        assert z == 13.6

    def test_unset_marker(self, cs_dummy):
        cs_dummy.unset_marker(Marker.LEFT_LEVEE_BANK.value)
        df_markers = cs_dummy.markers
        assert len(df_markers) == 2
        assert Marker.LEFT_LEVEE_BANK.value not in df_markers.marker.values

    @pytest.mark.parametrize(
        "x,z,expected_index",
        [
            (0, None, 0),
            (5, None, 0),
            (5, 20, 0),
            (5, 16.4, 1),
            (20, 13.6, 2),
            (20, None, 2),
            (50, 10, 5),
            (100, 20, 10),
        ],
    )
    def test_find_nearest_point_index(self, cs_dummy, x, z, expected_index):
        index = cs_dummy._find_nearest_point_index(x, z)
        assert index == expected_index

    def test_plot(self, cs_dummy):
        cs_dummy.plot()
