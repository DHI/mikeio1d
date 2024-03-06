import pytest

from typing import List

from IPython.terminal.interactiveshell import TerminalInteractiveShell

from mikeio1d.cross_sections import CrossSection
from mikeio1d.cross_sections import CrossSectionCollection

from .test_cross_section import create_xz_data


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


def create_dummy_cross_section(location_id, chainage, topo_id):
    x, z = create_xz_data()
    return CrossSection.from_xz(x, z, location_id=location_id, chainage=chainage, topo_id=topo_id)


@pytest.fixture
def dummy_cross_section():
    return create_dummy_cross_section("loc1", 100, "topo1")


@pytest.fixture
def many_dummy_cross_sections():
    xs = []
    for i in range(0, 100, 10):
        xs.append(create_dummy_cross_section(f"loc{i}", i, "topo"))
    for i in range(0, 100, 10):
        xs.append(create_dummy_cross_section(f"loc{i}", i, "topo2"))
    return xs


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
