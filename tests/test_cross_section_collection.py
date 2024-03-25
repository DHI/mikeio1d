import pytest

from typing import List

from IPython.terminal.interactiveshell import TerminalInteractiveShell

import pandas as pd

from mikeio1d import Xns11
from mikeio1d.cross_sections import CrossSection
from mikeio1d.cross_sections import CrossSectionCollection

from .test_cross_section import create_xz_data

from tests import testdata


@pytest.fixture()
def shell():
    shell = TerminalInteractiveShell()
    shell.run_cell(
        """
        from mikeio1d.cross_sections import CrossSectionCollection
        """
    )
    return shell


def complete(shell, prompt) -> List[str]:
    prompt, completions = shell.complete(prompt)
    completions = [c[len(prompt) :] for c in completions]
    return completions


def create_dummy_cross_section(location_id, chainage, topo_id) -> CrossSection:
    x, z = create_xz_data()
    return CrossSection.from_xz(x, z, location_id=location_id, chainage=chainage, topo_id=topo_id)


@pytest.fixture
def dummy_cross_section() -> CrossSection:
    return create_dummy_cross_section("loc1", 100, "topo1")


@pytest.fixture
def many_dummy_cross_sections() -> List[CrossSection]:
    xs = []
    for i in range(0, 100, 10):
        xs.append(create_dummy_cross_section(f"loc{i}", i, "topo"))
    for i in range(0, 100, 10):
        xs.append(create_dummy_cross_section(f"loc{i}", i, "topo2"))
    return xs


@pytest.fixture
def many_real_cross_sections() -> List[CrossSection]:
    xns = Xns11(testdata.mikep_xns11)
    return list(xns.xsections.values())


class TestCrossSectionCollectionUnits:
    """
    Unit tests for the CrossSectionCollection class.
    """

    def test_create_empty_collection(self):
        c = CrossSectionCollection()
        assert len(c) == 0

    def test_create_collection_from_list(self, many_dummy_cross_sections):
        csc = CrossSectionCollection(many_dummy_cross_sections)
        assert len(csc) == 20

    def test_create_collection_from_dict(self, dummy_cross_section):
        csc = CrossSectionCollection(
            {
                ("loc1", "100.000", "topo1"): dummy_cross_section,
            }
        )
        assert len(csc) == 1

        with pytest.raises(ValueError):
            csc = CrossSectionCollection(
                {
                    ("loc1", "100.000", "topo1"): dummy_cross_section,
                    ("not_matching_xs", "100.000", "topo1"): dummy_cross_section,
                }
            )

    def test_get_item(self, many_dummy_cross_sections):
        csc = CrossSectionCollection(many_dummy_cross_sections)
        assert csc["loc0", "0.000", "topo"] == many_dummy_cross_sections[0]
        assert csc["loc90", "90.000", "topo2"] == many_dummy_cross_sections[-1]

    @pytest.mark.parametrize("slice_char", [..., slice(None)])
    def test_get_item_slice(self, many_dummy_cross_sections, slice_char):
        csc = CrossSectionCollection(many_dummy_cross_sections)

        sliced = csc["loc0", slice_char, slice_char]
        assert len(csc["loc0", slice_char, slice_char]) == 2
        for xs in sliced.values():
            assert xs.location_id == "loc0"

        sliced = csc[slice_char, slice_char, "topo2"]
        assert len(sliced) == 10
        for xs in sliced.values():
            assert xs.topo_id == "topo2"

        sliced = csc[slice_char, "50.000", slice_char]
        assert len(sliced) == 2
        for xs in sliced.values():
            assert xs.chainage == 50

        sliced = csc["loc0"]
        assert len(sliced) == 2
        for xs in sliced.values():
            assert xs.location_id == "loc0"

        sliced = csc["loc50", "50.000"]
        assert len(sliced) == 2
        for xs in sliced.values():
            assert xs.location_id == "loc50"
            assert xs.chainage == 50

    @pytest.mark.parametrize(
        "prompt,expected_completions",
        [
            (
                "csc['",
                [
                    "loc0",
                    "loc10",
                    "loc20",
                    "loc30",
                    "loc40",
                    "loc50",
                    "loc60",
                    "loc70",
                    "loc80",
                    "loc90",
                ],
            ),
            (
                "csc['loc0', '",
                [
                    "0.000",
                ],
            ),
            (
                "csc['loc0', '0.000', '",
                ["topo", "topo2"],
            ),
        ],
    )
    def test_index_autocompletion(
        self, many_dummy_cross_sections, shell, prompt, expected_completions
    ):
        cross_sections = many_dummy_cross_sections
        shell.push({"csc": CrossSectionCollection(cross_sections)})
        completions = complete(shell, prompt)
        assert completions == expected_completions

    def test_joining_cross_section_collections(self, many_dummy_cross_sections):
        csc1 = CrossSectionCollection(many_dummy_cross_sections[:10])
        csc2 = CrossSectionCollection(many_dummy_cross_sections[10:])
        csc = csc1 | csc2
        assert len(csc) == 20

    def test_location_ids(self, many_dummy_cross_sections):
        csc = CrossSectionCollection(many_dummy_cross_sections)
        assert csc.location_ids == {
            "loc0",
            "loc10",
            "loc20",
            "loc30",
            "loc40",
            "loc50",
            "loc60",
            "loc70",
            "loc80",
            "loc90",
        }

    def test_chainages(self, many_dummy_cross_sections):
        csc = CrossSectionCollection(many_dummy_cross_sections)
        assert csc.chainages == {
            "0.000",
            "10.000",
            "20.000",
            "30.000",
            "40.000",
            "50.000",
            "60.000",
            "70.000",
            "80.000",
            "90.000",
        }

    def test_topo_ids(self, many_dummy_cross_sections):
        csc = CrossSectionCollection(many_dummy_cross_sections)
        assert csc.topo_ids == {"topo", "topo2"}

    def test_sel(self, many_dummy_cross_sections):
        csc = CrossSectionCollection(many_dummy_cross_sections)
        assert len(csc.sel(location_id="loc0")) == 2
        assert len(csc.sel(chainage="50.000")) == 2
        assert len(csc.sel(topo_id="topo2")) == 10
        assert len(csc.sel(location_id="loc0", topo_id="topo2")) == 1
        assert len(csc.sel(chainage="50.000", topo_id="topo2")) == 1
        assert len(csc.sel()) == 20

    def test_plot(self, many_dummy_cross_sections):
        csc = CrossSectionCollection(many_dummy_cross_sections[:3])
        csc.plot()

    def test_to_dataframe(self, many_dummy_cross_sections):
        csc = CrossSectionCollection(many_dummy_cross_sections)
        df = csc.to_dataframe()
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 20
        expected_columns = {"cross_section"}
        assert set(df.columns) == expected_columns
        expected_index_levels = {"location_id", "chainage", "topo_id"}
        assert set(df.index.names) == expected_index_levels
        xs_expected = many_dummy_cross_sections[0]
        xs = df.cross_section.iloc[0]
        assert xs == xs_expected

    def test_to_geopandas(self, many_real_cross_sections):
        pytest.importorskip("geopandas")
        import geopandas as gpd

        csc = CrossSectionCollection(many_real_cross_sections)
        csc = csc.sel(location_id="tributary")
        gdf = csc.to_geopandas()
        assert isinstance(gdf, gpd.GeoDataFrame)
        assert len(gdf) == len(csc)
        expected_columns = {
            "location_id",
            "chainage",
            "topo_id",
            "geometry",
        }
        assert set(gdf.columns) == expected_columns
        expected_geometry = list(csc.values())[0].geometry.to_shapely()
        assert gdf.geometry.iloc[0] == expected_geometry
        expected_geometry = list(csc.values())[-1].geometry.to_shapely()
        assert gdf.geometry.iloc[-1] == expected_geometry

    def test_to_geopandas_markers(self, many_real_cross_sections):
        pytest.importorskip("geopandas")
        import geopandas as gpd

        csc = CrossSectionCollection(many_real_cross_sections)
        csc = csc.sel(location_id="river")
        gdf = csc.to_geopandas_markers()
        assert isinstance(gdf, gpd.GeoDataFrame)
        assert len(gdf) == sum([len(cs.markers) for cs in csc.values()])
        expected_columns = {
            "location_id",
            "chainage",
            "topo_id",
            "marker",
            "marker_label",
            "geometry",
        }
        assert set(gdf.columns) == expected_columns
        expected_marker = list(csc.values())[0].markers
        assert gdf.marker.iloc[0] == str(expected_marker.marker[0])
        assert gdf.marker_label.iloc[0] == expected_marker.marker_label[0]

    def test_add_xsection(self, many_dummy_cross_sections):
        csc = CrossSectionCollection(many_dummy_cross_sections[:10])
        added_xs = many_dummy_cross_sections[10]
        csc.add_xsection(added_xs)
        assert len(csc) == 11
        assert added_xs in csc.values()
        assert (
            csc.sel(
                location_id=added_xs.location_id,
                chainage=added_xs.chainage,
                topo_id=added_xs.topo_id,
            )
            == added_xs
        )
