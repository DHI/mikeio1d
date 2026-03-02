"""Testing network mapper."""

import pytest
import networkx as nx
from pathlib import Path

from mikeio1d import Res1D
from mikeio1d.experimental import map_res1d_network
from mikeio1d.experimental._network_protocol import Network


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
    """Fixture providing Network instance."""
    return map_res1d_network(res1d_file)


@pytest.fixture
def network(mapper):
    """Fixture providing Network instance (alias for mapper)."""
    return mapper


class TestNetworkMapper:
    """Test Network functionality."""

    def test_mapper_initialization(self, res1d_file):
        """Test that Network initializes correctly."""
        mapper = map_res1d_network(res1d_file)
        assert mapper is not None
        assert hasattr(mapper, "_edges")

    def test_map_network_returns_generic_network(self, mapper):
        """Test that create_res1d_mapper returns a Network instance with a graph."""
        assert isinstance(mapper, Network)
        assert isinstance(mapper.graph, nx.Graph)

    @pytest.mark.skip("Need to fix the test after relabeling nodes to int")
    def test_all_res1d_nodes_mapped(self, res1d_object, network):
        """Test that all nodes from Res1D are present in the graph."""
        # Get all node IDs from the original Res1D
        original_node_ids = set(res1d_object.nodes.keys())

        # Get all node IDs in the graph (filter for actual nodes, not gridpoints)
        graph_node_ids = set()
        for node_id in network.graph.nodes():
            if node_id.startswith("node-"):
                # Extract original node ID from the mapped ID
                original_id = node_id.replace("node-", "")
                graph_node_ids.add(original_id)

        # Check that all original nodes are present
        assert original_node_ids.issubset(graph_node_ids), (
            f"Missing nodes: {original_node_ids - graph_node_ids}"
        )

    def test_graph_has_correct_node_count(self, res1d_object, network):
        """Test that graph has correct total number of nodes."""
        node_count = len(res1d_object.nodes)
        gridpoint_count = sum(
            max(0, len(reach.gridpoints) - 2) for reach in res1d_object.reaches.values()
        )
        expected_total = node_count + gridpoint_count

        actual_total = len(network.graph.nodes())

        assert actual_total == expected_total, (
            f"Expected {expected_total} total nodes, found {actual_total}"
        )

    def test_nodes_have_data_attribute(self, network):
        """Test that all nodes in the graph have data attribute."""
        for node_id, node_data in network.graph.nodes(data=True):
            assert "data" in node_data, f"Node {node_id} missing 'data' attribute"
            assert hasattr(node_data["data"], "columns"), (
                f"Node {node_id} data is not DataFrame-like"
            )

    def test_graph_is_connected(self, network):
        """Test that the resulting graph is connected."""
        # Note: This might not always be true for all networks,
        # but it's a good sanity check for most cases
        graph = network.graph
        if len(graph.nodes()) > 0:
            assert nx.is_connected(graph), "Graph should be connected"

    # reach '100l1': start='100', end='99', intermediate breakpoint at chainage ~23.84

    def test_find_node(self, mapper):
        """Test that find returns an integer id for a node lookup."""
        result = mapper.find(node="1")
        assert isinstance(result, int)

    def test_find_multiple_nodes(self, mapper):
        """Test that find returns a list of distinct integer ids for multiple nodes."""
        results = mapper.find(node=["1", "2"])
        assert isinstance(results, list)
        assert len(results) == 2
        assert all(isinstance(r, int) for r in results)
        assert results[0] != results[1]

    def test_find_breakpoint(self, mapper):
        """Test that find returns an integer id for a breakpoint lookup."""
        result = mapper.find(edge="100l1", distance=23.8413574216414)
        assert isinstance(result, int)

    def test_find_edge_start(self, mapper):
        """Test that find with distance='start' returns the start node id."""
        result = mapper.find(edge="100l1", distance="start")
        assert result == mapper.find(node="100")

    def test_find_edge_end(self, mapper):
        """Test that find with distance='end' returns the end node id."""
        result = mapper.find(edge="100l1", distance="end")
        assert result == mapper.find(node="99")

    def test_recall_node(self, mapper):
        """Test that recall returns the original node coordinates."""
        node_id = mapper.find(node="1")
        result = mapper.recall(node_id)
        assert result == {"node": "1"}

    def test_recall_breakpoint(self, mapper):
        """Test that recall returns the original edge and distance for a breakpoint."""
        bp_id = mapper.find(edge="100l1", distance=23.8413574216414)
        result = mapper.recall(bp_id)
        assert result["edge"] == "100l1"
        assert abs(result["distance"] - 23.8413574216414) < 1e-3

    def test_roundtrip_node(self, mapper):
        """Test that find -> recall round-trips correctly for a node."""
        original = {"node": "1"}
        recalled = mapper.recall(mapper.find(node=original["node"]))
        assert recalled == original

    def test_roundtrip_breakpoint(self, mapper):
        """Test that find -> recall round-trips correctly for a breakpoint."""
        original = {"edge": "100l1", "distance": 23.8413574216414}
        recalled = mapper.recall(mapper.find(edge=original["edge"], distance=original["distance"]))
        assert recalled["edge"] == original["edge"]
        assert abs(recalled["distance"] - original["distance"]) < 1e-3

    def test_roundtrip_multiple_nodes(self, mapper):
        """Test that find -> recall round-trips correctly for multiple nodes."""
        node_ids = ["1", "2", "3"]
        results = mapper.find(node=node_ids)
        recalled = mapper.recall(results)
        assert [r["node"] for r in recalled] == node_ids
