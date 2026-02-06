"""Testing network mapper."""

import pytest
import networkx as nx
from pathlib import Path

from mikeio1d import Res1D
from mikeio1d.result_network.format_mapper import NetworkMapper, GenericNetwork


@pytest.fixture
def res1d_file():
    """Fixture providing path to test Res1D file."""
    return "tests/testdata/network.res1d"


@pytest.fixture
def res1d_object(res1d_file):
    """Fixture providing Res1D object."""
    return Res1D(res1d_file)


@pytest.fixture
def mapper(res1d_file):
    """Fixture providing NetworkMapper instance."""
    return NetworkMapper(res1d_file)


@pytest.fixture
def network(mapper):
    """Fixture providing mapped GenericNetwork."""
    return mapper.map_network()


class TestNetworkMapper:
    """Test NetworkMapper functionality."""

    def test_mapper_initialization(self, res1d_file):
        """Test that NetworkMapper initializes correctly."""
        mapper = NetworkMapper(res1d_file)
        assert mapper is not None
        assert hasattr(mapper, "_nodes")
        assert hasattr(mapper, "_edges")

    def test_map_network_returns_generic_network(self, mapper):
        """Test that map_network returns GenericNetwork instance."""
        network = mapper.map_network()
        assert isinstance(network, GenericNetwork)
        assert isinstance(network.as_graph, nx.Graph)

    def test_all_res1d_nodes_mapped(self, res1d_object, network):
        """Test that all nodes from Res1D are present in the graph."""
        # Get all node IDs from the original Res1D
        original_node_ids = set(res1d_object.nodes.keys())

        # Get all node IDs in the graph (filter for actual nodes, not gridpoints)
        graph_node_ids = set()
        for node_id in network.as_graph.nodes():
            if node_id.startswith("node-"):
                # Extract original node ID from the mapped ID
                original_id = node_id.replace("node-", "")
                graph_node_ids.add(original_id)

        # Check that all original nodes are present
        assert original_node_ids.issubset(
            graph_node_ids
        ), f"Missing nodes: {original_node_ids - graph_node_ids}"

    def test_graph_has_correct_node_count(self, res1d_object, network):
        """Test that graph has correct total number of nodes."""
        node_count = len(res1d_object.nodes)
        gridpoint_count = sum(
            len(reach.gridpoints) for reach in res1d_object.reaches.values()
        ) - 2 * len(res1d_object.reaches)
        expected_total = node_count + gridpoint_count

        actual_total = len(network.as_graph.nodes())

        assert (
            actual_total == expected_total
        ), f"Expected {expected_total} total nodes, found {actual_total}"

    def test_nodes_have_data_attribute(self, network):
        """Test that all nodes in the graph have data attribute."""
        for node_id, node_data in network.as_graph.nodes(data=True):
            assert "data" in node_data, f"Node {node_id} missing 'data' attribute"
            assert hasattr(
                node_data["data"], "columns"
            ), f"Node {node_id} data is not DataFrame-like"

    def test_graph_is_connected(self, network):
        """Test that the resulting graph is connected."""
        # Note: This might not always be true for all networks,
        # but it's a good sanity check for most cases
        graph = network.as_graph
        if len(graph.nodes()) > 0:
            assert nx.is_connected(graph), "Graph should be connected"
