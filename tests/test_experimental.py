import pytest
import networkx as nx
from mikeio1d.experimental import to_networkx
from tests.conftest import res1d_network


class TestNetworkx:
    @pytest.mark.parametrize(
        "graph_type,expected_class",
        [
            ("MultiDiGraph", nx.MultiDiGraph),
            ("DiGraph", nx.DiGraph),
            ("MultiGraph", nx.MultiGraph),
            ("Graph", nx.Graph),
        ],
    )
    def test_to_networkx_graph_types(self, res1d_network, graph_type, expected_class):
        """Test that to_networkx returns the correct graph type with proper structure."""
        G = to_networkx(res1d_network, graph_type=graph_type)
        assert isinstance(G, expected_class)

        # Check number of nodes (should equal number of nodes in res1d)
        expected_nodes = len(res1d_network.network.nodes)
        assert len(G.nodes) == expected_nodes

        expected_edges = len(res1d_network.reaches)
        assert len(G.edges) == expected_edges

        # Check direction of sample edge
        sample_reach = next(iter(res1d_network.reaches.values()))
        start_node = sample_reach.start_node
        end_node = sample_reach.end_node
        assert G.has_edge(res1d_network.nodes[start_node], res1d_network.nodes[end_node])
