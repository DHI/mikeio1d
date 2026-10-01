"""Test reading and extracting a chosen set of quantities from a single location.

ResultLocation.add, read, to_dataframe, plot, to_csv, to_dfs0 and to_txt take a
`quantities` argument that narrows the location down to some of its quantities.
A reach is the interesting case, because one quantity id there spans several
gridpoints.
"""

import pytest
import pandas as pd

from matplotlib.axes import Axes
from pandas.testing import assert_frame_equal

from mikeio1d import Res1D

from .testdata import testdata


@pytest.fixture
def res():
    return Res1D(testdata.network_res1d)


@pytest.fixture
def res_catchments():
    return Res1D(testdata.catchments_res1d)


@pytest.fixture
def reach(res):
    """A reach with WaterLevel at two gridpoints and Discharge at one."""
    return res.reaches["100l1"]


@pytest.fixture
def node(res):
    return res.nodes["1"]


@pytest.fixture
def catchment(res_catchments):
    return res_catchments.catchments["100_16_16"]


@pytest.fixture
def structure(res):
    return res.structures["119w1"]


@pytest.fixture(params=["node", "reach", "catchment", "structure"])
def location(request):
    return request.getfixturevalue(request.param)


def _quantity_ids(df: pd.DataFrame) -> set[str]:
    return set(df.columns.get_level_values("quantity"))


class TestRead:
    def test_without_quantities_reads_every_quantity(self, location):
        df = location.read(column_mode="all")
        assert _quantity_ids(df) == set(location.quantities)

    def test_a_single_quantity_as_str(self, reach):
        df = reach.read(quantities="Discharge")
        assert_frame_equal(df, reach.Discharge.read())

    def test_a_quantity_spanning_several_gridpoints_reads_them_all(self, reach):
        df = reach.read(quantities="WaterLevel")
        assert len(df.columns) == 2
        assert_frame_equal(df, reach.WaterLevel.read())

    def test_a_list_of_quantities(self, catchment):
        quantities = ["TotalRunOff", "ActualRainfall"]
        df = catchment.read(column_mode="all", quantities=quantities)
        assert _quantity_ids(df) == set(quantities)

    def test_column_mode_stays_the_first_positional_argument(self, reach):
        df = reach.read("all")
        assert isinstance(df.columns, pd.MultiIndex)

    def test_column_mode_applies_to_the_selected_quantities(self, reach):
        df = reach.read(column_mode="timeseries", quantities="Discharge")
        assert [tsid.quantity for tsid in df.columns] == ["Discharge"]

    def test_a_repeated_quantity_is_read_once(self, reach):
        df = reach.read(quantities=["WaterLevel", "WaterLevel"])
        assert_frame_equal(df, reach.WaterLevel.read())

    def test_to_dataframe_is_an_alias(self, reach):
        expected = reach.read("all", quantities="WaterLevel")
        assert_frame_equal(reach.to_dataframe("all", quantities="WaterLevel"), expected)

    @pytest.mark.parametrize("method", ["read", "to_dataframe"])
    def test_quantities_is_keyword_only(self, reach, method):
        with pytest.raises(TypeError):
            getattr(reach, method)("all", "WaterLevel")


class TestUnknownQuantities:
    """An unknown quantity is refused rather than dropped.

    Dropping it could leave nothing to read, and Res1D treats an empty
    selection as 'read everything queued', so it is refused instead.
    """

    @pytest.mark.parametrize("method", ["add", "read", "to_dataframe", "plot"])
    def test_is_refused_by_every_method(self, node, method):
        with pytest.raises(ValueError, match="NotAQuantity"):
            getattr(node, method)(quantities="NotAQuantity")

    @pytest.mark.parametrize("method", ["to_csv", "to_dfs0", "to_txt"])
    def test_is_refused_before_a_file_is_written(self, node, method, tmp_path):
        file_path = tmp_path / f"out.{method.removeprefix('to_')}"
        with pytest.raises(ValueError, match="NotAQuantity"):
            getattr(node, method)(file_path, quantities="NotAQuantity")
        assert not file_path.exists()

    def test_names_what_the_location_does_have(self, reach):
        with pytest.raises(ValueError, match="WaterLevel.*Discharge"):
            reach.read(quantities="NotAQuantity")

    def test_one_unknown_among_known_is_still_refused(self, reach):
        with pytest.raises(ValueError, match="NotAQuantity"):
            reach.read(quantities=["Discharge", "NotAQuantity"])

    def test_a_quantity_of_another_location_is_refused(self, node):
        with pytest.raises(ValueError, match="Discharge"):
            node.read(quantities="Discharge")

    def test_an_empty_list_is_refused(self, reach):
        with pytest.raises(ValueError, match="At least one quantity"):
            reach.read(quantities=[])

    def test_a_location_without_quantities_says_so(self):
        res = Res1D(testdata.network_res1d, quantities=["WaterLevel"])
        structure = res.structures["119w1"]
        assert structure.quantities == []
        with pytest.raises(ValueError, match="has no quantities"):
            structure.read()


class TestAdd:
    def test_queues_only_the_selected_quantity(self, res, reach):
        reach.add("Discharge")
        expected = reach.read(column_mode="timeseries", quantities="Discharge").columns
        assert res.network.queue == list(expected)

    def test_without_quantities_queues_every_quantity(self, res, reach):
        reach.add()
        assert len(res.network.queue) == 3

    def test_queued_quantities_are_read_by_res1d(self, res, reach, node):
        reach.add("Discharge")
        node.add()
        df = res.read(column_mode="all")
        assert list(df.columns.get_level_values("quantity")) == ["Discharge", "WaterLevel"]


class TestPlot:
    def test_returns_the_axes(self, reach):
        ax = reach.plot(quantities="WaterLevel")
        assert isinstance(ax, Axes)
        assert len(ax.get_lines()) == 2

    def test_plots_onto_given_axes(self, reach):
        ax = reach.plot(quantities="Discharge")
        same_ax = reach.plot(ax=ax, quantities="WaterLevel")
        assert same_ax is ax
        assert len(ax.get_lines()) == 3

    def test_labels_the_y_axis_with_a_single_quantity(self, reach):
        ax = reach.plot(quantities="WaterLevel")
        assert "Water level" in ax.get_ylabel()

    def test_leaves_the_y_axis_unlabelled_with_mixed_quantities(self, reach):
        ax = reach.plot()
        assert ax.get_ylabel() == ""

    def test_clears_a_stale_y_axis_label_with_mixed_quantities(self, reach):
        ax = reach.plot(quantities="WaterLevel")
        reach.plot(ax=ax)
        assert ax.get_ylabel() == ""

    def test_passes_keyword_arguments_to_pandas(self, reach):
        ax = reach.plot(quantities="Discharge", title="A title")
        assert ax.get_title() == "A title"


class TestExtract:
    def test_to_csv_writes_only_the_selected_quantity(self, reach, tmp_path):
        file_path = tmp_path / "out.csv"
        reach.to_csv(file_path, quantities="Discharge")
        header = file_path.read_text().splitlines()[2]
        assert header.split(";")[1:-1] == ["Discharge"]

    def test_to_txt_writes_every_gridpoint_of_the_quantity(self, reach, tmp_path):
        file_path = tmp_path / "out.txt"
        reach.to_txt(file_path, quantities="WaterLevel")
        header = file_path.read_text().splitlines()[1]
        assert header.split()[1:] == ["WaterLevel", "WaterLevel"]

    def test_without_quantities_writes_every_quantity(self, reach, tmp_path):
        file_path = tmp_path / "out.csv"
        reach.to_csv(file_path)
        header = file_path.read_text().splitlines()[2]
        assert sorted(header.split(";")[1:-1]) == ["Discharge", "WaterLevel", "WaterLevel"]

    def test_time_step_skipping_number_is_passed_on(self, reach, tmp_path):
        every, tenth = tmp_path / "every.txt", tmp_path / "tenth.txt"
        reach.to_txt(every, quantities="Discharge")
        reach.to_txt(tenth, 10, quantities="Discharge")
        n_every = len(every.read_text().splitlines())
        n_tenth = len(tenth.read_text().splitlines())
        assert n_tenth < n_every

    def test_to_dfs0_matches_res1d_for_the_same_quantity(self, res, reach, tmp_path):
        from_location = tmp_path / "location.dfs0"
        from_res1d = tmp_path / "res1d.dfs0"
        everything = tmp_path / "everything.dfs0"
        reach.to_dfs0(from_location, quantities="Discharge")
        discharge = reach.read(column_mode="timeseries", quantities="Discharge").columns
        res.to_dfs0(from_res1d, list(discharge))
        reach.to_dfs0(everything)
        size = from_location.stat().st_size
        assert size == from_res1d.stat().st_size
        assert size < everything.stat().st_size
