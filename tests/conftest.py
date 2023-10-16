import pytest

from mikeio1d.res1d import Res1D
from mikeio1d.result_network import ResultNode, ResultReach, ResultCatchment
from mikeio1d.dotnet import pythonnet_implementation as impl

from .testdata import testdata


@pytest.fixture()
def res1d_network():
    return Res1D(testdata.Network_res1d)


@pytest.fixture()
def res1d_catchments():
    return Res1D(testdata.Catchments_res1d)


@pytest.fixture
def node(res1d_network):
    dotnet_node = impl(res1d_network.data.Nodes[0])
    return ResultNode(dotnet_node, res1d_network)


@pytest.fixture
def many_nodes(res1d_network):
    nodes = res1d_network.result_network.nodes
    return [
        getattr(nodes, n)
        for n in nodes.__dict__.keys()
        if n.startswith(nodes.node_label)
    ]


@pytest.fixture
def reach(res1d_network):
    dotnet_reach = impl(res1d_network.data.Reaches)
    return ResultReach(dotnet_reach, res1d_network)


@pytest.fixture
def many_reaches(res1d_network):
    reaches = res1d_network.result_network.reaches
    return [
        getattr(reaches, r)
        for r in reaches.__dict__.keys()
        if r.startswith(reaches.reach_label)
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
