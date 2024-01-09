import pytest

from pandas.testing import assert_index_equal
from pandas.testing import assert_series_equal

from mikeio1d.res1d import Res1D
from mikeio1d.result_network import ResultNode
from mikeio1d.result_network import ResultCatchment
from mikeio1d.dotnet import pythonnet_implementation as impl

from .testdata import testdata


class Helpers:
    """
    Class containing helper methods for performing tests.
    """

    @staticmethod
    def assert_shared_columns_equal(df_ref, df):
        """
        Compares columns in df to the ones in df_ref.

        Note that df_ref typically has more columns than df.
        Comparison is performed only in columns of df.
        """
        assert_index_equal(df_ref.index, df.index)
        for col in df:
            # TODO: Replace with assert_series_equal(df[col], df_ref[col]) - this fails now since columns are not guaranteed unique
            diff = (df[[col]] - df_ref[[col]]).abs().sum()

            # TODO: Handle cases of different types than float
            try:
                diff = float(diff)
            except:
                continue

            assert pytest.approx(diff) == 0.0


@pytest.fixture
def helpers():
    return Helpers


@pytest.fixture()
def flow_split_file_path():
    return testdata.flow_split_res1d


@pytest.fixture()
def res1d_network():
    return Res1D(testdata.network_res1d)


@pytest.fixture()
def res1d_river_network():
    return Res1D(testdata.network_river_res1d)


@pytest.fixture()
def res1d_catchments():
    return Res1D(testdata.catchments_res1d)


@pytest.fixture
def node(res1d_network):
    dotnet_node = impl(res1d_network.data.Nodes[0])
    return ResultNode(dotnet_node, res1d_network)


@pytest.fixture
def many_nodes(res1d_network):
    nodes = res1d_network.result_network.nodes
    return [getattr(nodes, n) for n in nodes.__dict__.keys() if n.startswith(nodes.node_label)]


@pytest.fixture
def reach(res1d_network):
    return res1d_network.result_network.reaches.r_100l1


@pytest.fixture
def river_reach(res1d_river_network):
    return res1d_river_network.result_network.reaches.river


@pytest.fixture
def many_reaches(res1d_network):
    reaches = res1d_network.result_network.reaches
    return [
        getattr(reaches, r) for r in reaches.__dict__.keys() if r.startswith(reaches.reach_label)
    ]


@pytest.fixture
def catchment(res1d_catchments):
    dotnet_catchment = impl(res1d_catchments.data.Catchments[0])
    return ResultCatchment(dotnet_catchment, res1d_catchments)


@pytest.fixture
def many_catchments(res1d_catchments):
    catchments = res1d_catchments.result_network.catchments
    return [
        getattr(catchments, c)
        for c in catchments.__dict__.keys()
        if c.startswith(catchments.catchment_label)
    ]


@pytest.fixture
def structure(res1d_network):
    return res1d_network.result_network.structures["119w1"]
