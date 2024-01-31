import pytest

import pandas as pd

from mikeio1d import Res1D

from mikeio1d.quantities import TimeSeriesId
from mikeio1d.quantities import TimeSeriesIdGroup

from mikeio1d.result_network.data_entry import DataEntry
from mikeio1d.result_network.result_quantity import ResultQuantity
from mikeio1d.result_network.result_reach import ResultReach

from mikeio1d.query import QueryData
from mikeio1d.query import QueryDataCatchment
from mikeio1d.query import QueryDataGlobal
from mikeio1d.query import QueryDataNode
from mikeio1d.query import QueryDataReach
from mikeio1d.query import QueryDataStructure
from mikeio1d.query import QueryDataCreator

from mikeio1d.result_reader_writer.result_reader import ColumnMode

from mikeio1d.dotnet import pythonnet_implementation as impl


@pytest.fixture
def time_series_id():
    """Fictional TimeSeriesId for testing."""
    return TimeSeriesId(
        quantity="Discharge",
        group="Node",
        name="Node1",
        chainage=10.0,
        tag="Tag1",
        duplicate=0,
        derived=False,
    )


@pytest.fixture
def time_series_id_valid_river_res1d():
    """TimeSeriesId for a that exists in network river res1d results."""
    return TimeSeriesId(
        quantity="Discharge",
        group="Reach",
        name="basin_left1",
        chainage=1.002,
        tag="0.0-246.6",
    )


@pytest.fixture
def time_series_id_invalid_river_res1d():
    """TimeSeriesId for a that does not exist in network river res1d results."""
    return TimeSeriesId(
        quantity="I do not exist",
        group="Reach",
        name="I do not exist",
        chainage=1.002,
        tag="Tag1",
        duplicate=0,
        derived=False,
    )


def test_time_series_id_equality(time_series_id, time_series_id_valid_river_res1d):
    time_series_id_equal = TimeSeriesId(
        quantity="Discharge",
        group="Node",
        name="Node1",
        chainage=10.0,
        tag="Tag1",
        duplicate=0,
        derived=False,
    )
    assert id(time_series_id) != id(time_series_id_equal)

    assert time_series_id == time_series_id
    assert time_series_id != list()
    assert time_series_id == time_series_id_equal
    assert time_series_id == time_series_id_equal
    assert time_series_id != time_series_id_valid_river_res1d


def test_timeseries_id_equality_with_groups():
    tsid1 = TimeSeriesId(
        quantity="Discharge",
        group="Node",
        name="Node1",
    )
    tsid2 = TimeSeriesId(
        quantity="Discharge",
        group=TimeSeriesIdGroup.NODE,
        name="Node1",
    )
    assert tsid1 == tsid2


def test_time_series_id_hash(time_series_id):
    time_series_id2 = TimeSeriesId(
        quantity="Discharge",
        group="Node",
        name="Node1",
        chainage=10.0,
        tag="Tag1",
        duplicate=0,
        derived=False,
    )
    time_series_id3 = TimeSeriesId(
        quantity="Discharge",
        group=TimeSeriesIdGroup.NODE,
        name="Node1",
        chainage=10.0,
        tag="Tag1",
        duplicate=0,
        derived=False,
    )
    assert hash(time_series_id) == hash(time_series_id2)
    assert hash(time_series_id) == hash(time_series_id3)
    assert hash(time_series_id) != hash(time_series_id_valid_river_res1d)


def test_time_series_id_is_valid(
    res1d_river_network, time_series_id_valid_river_res1d, time_series_id_invalid_river_res1d
):
    """Test if a TimeSeriesId is valid for a Res1D object (e.g. it exists in the result file)."""
    assert time_series_id_valid_river_res1d.is_valid(res1d_river_network)
    assert not time_series_id_invalid_river_res1d.is_valid(res1d_river_network)


def test_time_series_id_astuple(time_series_id):
    expected_tuple = ("Discharge", "Node", "Node1", 10.0, "Tag1", 0, False)
    assert time_series_id.astuple() == expected_tuple


def test_time_series_id_to_data_entry(res1d_river_network, time_series_id_valid_river_res1d):
    with pytest.raises(TypeError):
        # requires res1d context
        time_series_id_valid_river_res1d.to_data_entry()
    m1d = time_series_id_valid_river_res1d.to_data_entry(res1d_river_network)
    assert isinstance(m1d, DataEntry)
    assert m1d.m1d_dataset.Name == "basin_left1"
    assert m1d.data_item.Quantity.Id == "Discharge"
    assert m1d.element_index == 0


def test_time_series_id_to_m1d_errors_for_derived_quantity(res1d_river_network):
    tsid = TimeSeriesId(
        quantity="Discharge",
        group="Reach",
        name="basin_left1",
        chainage=1.002,
        derived=True,
    )
    with pytest.raises(ValueError):
        tsid.to_data_entry(res1d_river_network)


def test_time_series_id_to_result_quantity(res1d_river_network, time_series_id_valid_river_res1d):
    with pytest.raises(TypeError):
        # requires res1d context
        time_series_id_valid_river_res1d.to_result_quantity()
    result_quantity = time_series_id_valid_river_res1d.to_result_quantity(res1d_river_network)
    assert isinstance(result_quantity, ResultQuantity)
    assert result_quantity.m1d_dataset.Name == "basin_left1"
    assert result_quantity.data_item.Quantity.Id == "Discharge"
    assert result_quantity.element_index == 0


def test_time_series_id_to_result_quantity_errors_for_derived_quantity(res1d_river_network):
    tsid = TimeSeriesId(
        quantity="Discharge",
        group="Reach",
        name="basin_left1",
        chainage=1.002,
        derived=True,
    )
    with pytest.raises(ValueError):
        tsid.to_result_quantity(res1d_river_network)


def assert_queries_equal(query1: QueryData, query2: QueryData):
    """Assert that two queries are equal."""

    assert isinstance(query1, type(query2))
    assert query1.name == query2.name
    assert query1.quantity == query2.quantity
    if hasattr(query1, "chainage"):
        assert query1.chainage == query2.chainage
    if hasattr(query1, "structure"):
        assert query1.structure == query2.structure


@pytest.mark.parametrize(
    ["tsid", "expected_query"],
    [
        (TimeSeriesId("WaterLevel", "Node", "Node1"), QueryDataNode("WaterLevel", "Node1")),
        (
            TimeSeriesId("WaterLevel", "Reach", "Reach1", 10.0),
            QueryDataReach("WaterLevel", "Reach1", 10.0),
        ),
        (
            TimeSeriesId("WaterLevel", "Catchment", "Catchment1"),
            QueryDataCatchment("WaterLevel", "Catchment1"),
        ),
        (
            TimeSeriesId("WaterLevel", "Global"),
            QueryDataGlobal("WaterLevel"),
        ),
        (
            TimeSeriesId("Discharge", "Structure", "Structure1", tag="River"),
            QueryDataStructure("Discharge", "Structure1", "River"),
        ),
    ],
)
def test_time_series_id_to_query(tsid, expected_query):
    query = QueryDataCreator.from_timeseries_id(tsid)
    assert_queries_equal(query, expected_query)


def test_time_series_id_to_query_errors_for_derived_quantity():
    tsid = TimeSeriesId(
        quantity="Discharge",
        group="Reach",
        name="basin_left1",
        chainage=1.002,
        derived=True,
    )
    with pytest.raises(ValueError):
        QueryDataCreator.from_timeseries_id(tsid)


def test_time_series_id_next_duplicate(time_series_id):
    next_duplicate = time_series_id.next_duplicate()
    assert next_duplicate.duplicate == time_series_id.duplicate + 1
    next_next_duplicate = next_duplicate.next_duplicate()
    assert next_next_duplicate.duplicate == time_series_id.duplicate + 2


def test_time_series_id_prev_duplicate(time_series_id):
    with pytest.raises(ValueError):
        # duplicate cannot be negative
        time_series_id.prev_duplicate()

    next_duplicate = time_series_id.next_duplicate()
    assert next_duplicate.prev_duplicate() == time_series_id


def test_time_series_id_chainage_nan():
    """Chainage must be either float or nan."""
    with pytest.raises(ValueError):
        TimeSeriesId(
            quantity="Discharge",
            group="Reach",
            name="basin_left1",
            chainage=None,
        )
    with pytest.raises(ValueError):
        TimeSeriesId(
            quantity="Discharge",
            group="Reach",
            name="basin_left1",
            chainage="",
        )
    with pytest.raises(ValueError):
        TimeSeriesId(
            quantity="Discharge",
            group="Reach",
            name="basin_left1",
            chainage="chainage: 100.0",
        )


@pytest.mark.parametrize(
    ["query", "expected_tsid"],
    [
        (QueryDataNode("Discharge", "Node1"), TimeSeriesId("Discharge", "Node", "Node1")),
        (
            QueryDataReach("Discharge", "Reach1", 10.0),
            TimeSeriesId("Discharge", "Reach", "Reach1", 10.0),
        ),
        (
            QueryDataCatchment("Discharge", "Catchment1"),
            TimeSeriesId("Discharge", "Catchment", "Catchment1"),
        ),
        (QueryDataGlobal("Discharge"), TimeSeriesId("Discharge", "Global")),
        (
            QueryDataStructure("Discharge", "Structure1", "River"),
            TimeSeriesId("Discharge", "Structure", "Structure1", tag="River"),
        ),
    ],
)
def test_time_series_id_from_query(query, expected_tsid):
    tsid = TimeSeriesId.from_query(query)
    assert tsid == expected_tsid


def test_time_series_id_from_tuple():
    t = ("Discharge", "Node", "Node1", 10.0, "Tag1", 0, False)
    time_series_id = TimeSeriesId.from_tuple(t)
    assert time_series_id.name == "Node1"
    assert time_series_id.quantity == "Discharge"


def test_time_series_id_to_multiindex():
    time_series_ids = [
        TimeSeriesId(
            quantity="Discharge",
            group="Node",
            name="Node1",
            chainage=10.0,
            tag="Tag1",
            duplicate=0,
            derived=False,
        ),
        TimeSeriesId(
            quantity="Discharge",
            group="Node",
            name="Node2",
            chainage=20.0,
            tag="Tag2",
            duplicate=0,
            derived=False,
        ),
    ]
    multiindex = TimeSeriesId.to_multiindex(time_series_ids)
    assert len(multiindex) == 2
    assert multiindex[0] == ("Discharge", "Node", "Node1", 10.0, "Tag1", 0, False)
    assert multiindex[1] == ("Discharge", "Node", "Node2", 20.0, "Tag2", 0, False)


def test_time_series_id_from_multiindex():
    multiindex = pd.MultiIndex.from_tuples(
        [
            ("Discharge", "Node", "Node1", 10.0, "Tag1", 0, False),
            ("Discharge", "Node", "Node2", 20.0, "Tag2", 0, False),
        ],
        names=["quantity", "group", "name", "chainage", "tag", "duplicate", "derived"],
    )
    time_series_ids = TimeSeriesId.from_multiindex(multiindex)
    assert len(time_series_ids) == 2
    assert time_series_ids[0].name == "Node1"
    assert time_series_ids[0].quantity == "Discharge"
    assert time_series_ids[1].name == "Node2"
    assert time_series_ids[1].quantity == "Discharge"


def test_time_series_id_from_multiindex_compact():
    multiindex = pd.MultiIndex.from_tuples(
        [
            ("Discharge", "Node", "Node1"),
            ("Discharge", "Node", "Node2"),
        ],
        names=["quantity", "group", "name"],
    )
    expected = [
        TimeSeriesId("Discharge", "Node", "Node1"),
        TimeSeriesId("Discharge", "Node", "Node2"),
    ]
    time_series_ids = TimeSeriesId.from_multiindex(multiindex)
    assert len(time_series_ids) == 2
    for tsid, expected_tsid in zip(time_series_ids, expected):
        assert tsid == expected_tsid


def test_time_series_id_from_dataset_dataitem_and_element(reach: ResultReach):
    m1d_data_set = reach.reaches[0]
    m1d_data_item = m1d_data_set.DataItems[0]
    element_index = 0
    time_series_id = TimeSeriesId.from_dataset_dataitem_and_element(
        m1d_data_set, m1d_data_item, element_index
    )
    expected_time_series_id = TimeSeriesId(
        quantity="WaterLevel",
        group="Reach",
        name="100l1",
        chainage=0,
        tag="0.0-47.7",
        duplicate=0,
        derived=False,
    )
    assert time_series_id == expected_time_series_id


def test_time_series_id_from_result_quantity(res1d_river_network: Res1D):
    quantity_map = res1d_river_network.result_network.result_quantity_map
    for expected_tsid, quantity in quantity_map.items():
        if expected_tsid.duplicate > 0:
            # skip duplicates, this method does not support duplicates
            continue
        time_series_id = TimeSeriesId.from_result_quantity(quantity)
        assert time_series_id == expected_tsid


def test_time_series_id_get_dataset_name(reach: ResultReach):
    m1d_data_set = reach.reaches[0]
    name = TimeSeriesId.get_dataset_name(m1d_data_set, "ItemId")
    assert name == "ItemId:100l1"
