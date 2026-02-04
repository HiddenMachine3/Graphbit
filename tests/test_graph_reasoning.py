"""
Phase 2: Knowledge Graph Reasoning Tests

Comprehensive unit tests for graph reasoning operations added to the Graph model.
"""

import pytest
from pydantic import ValidationError

from src.models import Graph, Node, Edge, EdgeType


# ============================================================
# NEIGHBOR QUERY TESTS
# ============================================================


class TestNeighborQueries:
    """Tests for neighbor query methods."""
    
    def test_get_outgoing_neighbors_single_edge(self):
        """Should return single outgoing neighbor."""
        graph = Graph()
        
        node_a = Node(id="A", topic_name="Topic A")
        node_b = Node(id="B", topic_name="Topic B")
        
        graph.add_node(node_a)
        graph.add_node(node_b)
        graph.add_edge(Edge(from_node_id="A", to_node_id="B", weight=0.5, type=EdgeType.PREREQUISITE))
        
        neighbors = graph.get_outgoing_neighbors("A")
        assert neighbors == ["B"]
    
    def test_get_outgoing_neighbors_multiple_edges(self):
        """Should return all outgoing neighbors."""
        graph = Graph()
        
        for node_id in ["A", "B", "C", "D"]:
            graph.add_node(Node(id=node_id, topic_name=f"Topic {node_id}"))
        
        # A -> B, A -> C, A -> D
        graph.add_edge(Edge(from_node_id="A", to_node_id="B", weight=0.5, type=EdgeType.PREREQUISITE))
        graph.add_edge(Edge(from_node_id="A", to_node_id="C", weight=0.5, type=EdgeType.DEPENDS_ON))
        graph.add_edge(Edge(from_node_id="A", to_node_id="D", weight=0.5, type=EdgeType.APPLIED_WITH))
        
        neighbors = graph.get_outgoing_neighbors("A")
        assert set(neighbors) == {"B", "C", "D"}
    
    def test_get_outgoing_neighbors_no_edges(self):
        """Should return empty list if no outgoing edges."""
        graph = Graph()
        node_a = Node(id="A", topic_name="Topic A")
        graph.add_node(node_a)
        
        neighbors = graph.get_outgoing_neighbors("A")
        assert neighbors == []
    
    def test_get_outgoing_neighbors_nonexistent_node(self):
        """Should raise error if node doesn't exist."""
        graph = Graph()
        
        with pytest.raises(KeyError, match="not found"):
            graph.get_outgoing_neighbors("X")
    
    def test_get_incoming_neighbors_single_edge(self):
        """Should return single incoming neighbor."""
        graph = Graph()
        
        node_a = Node(id="A", topic_name="Topic A")
        node_b = Node(id="B", topic_name="Topic B")
        
        graph.add_node(node_a)
        graph.add_node(node_b)
        graph.add_edge(Edge(from_node_id="A", to_node_id="B", weight=0.5, type=EdgeType.PREREQUISITE))
        
        neighbors = graph.get_incoming_neighbors("B")
        assert neighbors == ["A"]
    
    def test_get_incoming_neighbors_multiple_edges(self):
        """Should return all incoming neighbors."""
        graph = Graph()
        
        for node_id in ["A", "B", "C", "D"]:
            graph.add_node(Node(id=node_id, topic_name=f"Topic {node_id}"))
        
        # A -> D, B -> D, C -> D
        graph.add_edge(Edge(from_node_id="A", to_node_id="D", weight=0.5, type=EdgeType.PREREQUISITE))
        graph.add_edge(Edge(from_node_id="B", to_node_id="D", weight=0.5, type=EdgeType.DEPENDS_ON))
        graph.add_edge(Edge(from_node_id="C", to_node_id="D", weight=0.5, type=EdgeType.APPLIED_WITH))
        
        neighbors = graph.get_incoming_neighbors("D")
        assert set(neighbors) == {"A", "B", "C"}
    
    def test_get_incoming_neighbors_no_edges(self):
        """Should return empty list if no incoming edges."""
        graph = Graph()
        node_a = Node(id="A", topic_name="Topic A")
        graph.add_node(node_a)
        
        neighbors = graph.get_incoming_neighbors("A")
        assert neighbors == []
    
    def test_get_incoming_neighbors_nonexistent_node(self):
        """Should raise error if node doesn't exist."""
        graph = Graph()
        
        with pytest.raises(KeyError, match="not found"):
            graph.get_incoming_neighbors("X")
    
    def test_get_neighbors_by_edge_type_single_type(self):
        """Should return neighbors connected by specified edge type."""
        graph = Graph()
        
        for node_id in ["A", "B", "C"]:
            graph.add_node(Node(id=node_id, topic_name=f"Topic {node_id}"))
        
        # A -PREREQ-> B, A -DEPENDS_ON-> C
        graph.add_edge(Edge(from_node_id="A", to_node_id="B", weight=0.5, type=EdgeType.PREREQUISITE))
        graph.add_edge(Edge(from_node_id="A", to_node_id="C", weight=0.5, type=EdgeType.DEPENDS_ON))
        
        neighbors = graph.get_neighbors_by_edge_type("A", {EdgeType.PREREQUISITE})
        assert neighbors == ["B"]
    
    def test_get_neighbors_by_edge_type_multiple_types(self):
        """Should return neighbors connected by any allowed edge type."""
        graph = Graph()
        
        for node_id in ["A", "B", "C", "D"]:
            graph.add_node(Node(id=node_id, topic_name=f"Topic {node_id}"))
        
        # A -PREREQ-> B, A -DEPENDS_ON-> C, A -APPLIED_WITH-> D
        graph.add_edge(Edge(from_node_id="A", to_node_id="B", weight=0.5, type=EdgeType.PREREQUISITE))
        graph.add_edge(Edge(from_node_id="A", to_node_id="C", weight=0.5, type=EdgeType.DEPENDS_ON))
        graph.add_edge(Edge(from_node_id="A", to_node_id="D", weight=0.5, type=EdgeType.APPLIED_WITH))
        
        neighbors = graph.get_neighbors_by_edge_type("A", {EdgeType.PREREQUISITE, EdgeType.DEPENDS_ON})
        assert set(neighbors) == {"B", "C"}
    
    def test_get_neighbors_by_edge_type_no_match(self):
        """Should return empty list if no edges match."""
        graph = Graph()
        
        for node_id in ["A", "B"]:
            graph.add_node(Node(id=node_id, topic_name=f"Topic {node_id}"))
        
        graph.add_edge(Edge(from_node_id="A", to_node_id="B", weight=0.5, type=EdgeType.PREREQUISITE))
        
        neighbors = graph.get_neighbors_by_edge_type("A", {EdgeType.SUBCONCEPT_OF})
        assert neighbors == []
    
    def test_get_neighbors_by_edge_type_nonexistent_node(self):
        """Should raise error if node doesn't exist."""
        graph = Graph()
        
        with pytest.raises(KeyError, match="not found"):
            graph.get_neighbors_by_edge_type("X", {EdgeType.PREREQUISITE})


# ============================================================
# PATH EXISTENCE TESTS
# ============================================================


class TestPathExistence:
    """Tests for path_exists method."""
    
    def test_path_exists_direct_connection(self):
        """Should find direct path between connected nodes."""
        graph = Graph()
        
        node_a = Node(id="A", topic_name="Topic A")
        node_b = Node(id="B", topic_name="Topic B")
        
        graph.add_node(node_a)
        graph.add_node(node_b)
        graph.add_edge(Edge(from_node_id="A", to_node_id="B", weight=0.5, type=EdgeType.PREREQUISITE))
        
        assert graph.path_exists("A", "B", max_hops=1) is True
    
    def test_path_exists_multi_hop(self):
        """Should find path through intermediate nodes."""
        graph = Graph()
        
        # A -> B -> C
        for node_id in ["A", "B", "C"]:
            graph.add_node(Node(id=node_id, topic_name=f"Topic {node_id}"))
        
        graph.add_edge(Edge(from_node_id="A", to_node_id="B", weight=0.5, type=EdgeType.PREREQUISITE))
        graph.add_edge(Edge(from_node_id="B", to_node_id="C", weight=0.5, type=EdgeType.PREREQUISITE))
        
        assert graph.path_exists("A", "C", max_hops=2) is True
    
    def test_path_exists_respects_max_hops(self):
        """Should not find path beyond max_hops."""
        graph = Graph()
        
        # A -> B -> C -> D
        for node_id in ["A", "B", "C", "D"]:
            graph.add_node(Node(id=node_id, topic_name=f"Topic {node_id}"))
        
        graph.add_edge(Edge(from_node_id="A", to_node_id="B", weight=0.5, type=EdgeType.PREREQUISITE))
        graph.add_edge(Edge(from_node_id="B", to_node_id="C", weight=0.5, type=EdgeType.PREREQUISITE))
        graph.add_edge(Edge(from_node_id="C", to_node_id="D", weight=0.5, type=EdgeType.PREREQUISITE))
        
        assert graph.path_exists("A", "D", max_hops=2) is False
        assert graph.path_exists("A", "D", max_hops=3) is True
    
    def test_path_exists_no_connection(self):
        """Should return False if no path exists."""
        graph = Graph()
        
        node_a = Node(id="A", topic_name="Topic A")
        node_b = Node(id="B", topic_name="Topic B")
        
        graph.add_node(node_a)
        graph.add_node(node_b)
        
        assert graph.path_exists("A", "B", max_hops=5) is False
    
    def test_path_exists_with_edge_type_filter(self):
        """Should only follow allowed edge types."""
        graph = Graph()
        
        # A -PREREQ-> B -DEPENDS_ON-> C
        for node_id in ["A", "B", "C"]:
            graph.add_node(Node(id=node_id, topic_name=f"Topic {node_id}"))
        
        graph.add_edge(Edge(from_node_id="A", to_node_id="B", weight=0.5, type=EdgeType.PREREQUISITE))
        graph.add_edge(Edge(from_node_id="B", to_node_id="C", weight=0.5, type=EdgeType.DEPENDS_ON))
        
        # Following only PREREQUISITE should not reach C
        assert graph.path_exists("A", "C", max_hops=2, allowed_edge_types={EdgeType.PREREQUISITE}) is False
        
        # Following both types should reach C
        assert graph.path_exists("A", "C", max_hops=2, allowed_edge_types={EdgeType.PREREQUISITE, EdgeType.DEPENDS_ON}) is True
    
    def test_path_exists_all_edge_types_when_none(self):
        """Should follow all edge types when allowed_edge_types is None."""
        graph = Graph()
        
        # A -PREREQ-> B -DEPENDS_ON-> C
        for node_id in ["A", "B", "C"]:
            graph.add_node(Node(id=node_id, topic_name=f"Topic {node_id}"))
        
        graph.add_edge(Edge(from_node_id="A", to_node_id="B", weight=0.5, type=EdgeType.PREREQUISITE))
        graph.add_edge(Edge(from_node_id="B", to_node_id="C", weight=0.5, type=EdgeType.DEPENDS_ON))
        
        assert graph.path_exists("A", "C", max_hops=2, allowed_edge_types=None) is True
    
    def test_path_exists_same_node(self):
        """Should return True if from and to are the same."""
        graph = Graph()
        
        node_a = Node(id="A", topic_name="Topic A")
        graph.add_node(node_a)
        
        assert graph.path_exists("A", "A", max_hops=1) is True
    
    def test_path_exists_nonexistent_from_node(self):
        """Should raise error if from_node doesn't exist."""
        graph = Graph()
        node_b = Node(id="B", topic_name="Topic B")
        graph.add_node(node_b)
        
        with pytest.raises(KeyError, match="not found"):
            graph.path_exists("X", "B", max_hops=1)
    
    def test_path_exists_nonexistent_to_node(self):
        """Should raise error if to_node doesn't exist."""
        graph = Graph()
        node_a = Node(id="A", topic_name="Topic A")
        graph.add_node(node_a)
        
        with pytest.raises(KeyError, match="not found"):
            graph.path_exists("A", "X", max_hops=1)
    
    def test_path_exists_invalid_max_hops_zero(self):
        """Should raise error if max_hops is 0."""
        graph = Graph()
        node_a = Node(id="A", topic_name="Topic A")
        graph.add_node(node_a)
        
        with pytest.raises(ValueError, match="max_hops must be >= 1"):
            graph.path_exists("A", "A", max_hops=0)
    
    def test_path_exists_invalid_max_hops_negative(self):
        """Should raise error if max_hops is negative."""
        graph = Graph()
        node_a = Node(id="A", topic_name="Topic A")
        graph.add_node(node_a)
        
        with pytest.raises(ValueError, match="max_hops must be >= 1"):
            graph.path_exists("A", "A", max_hops=-1)
    
    def test_path_exists_handles_cycles(self):
        """Should handle graphs with cycles correctly."""
        graph = Graph()
        
        # A -> B -> C -> A (cycle)
        for node_id in ["A", "B", "C"]:
            graph.add_node(Node(id=node_id, topic_name=f"Topic {node_id}"))
        
        graph.add_edge(Edge(from_node_id="A", to_node_id="B", weight=0.5, type=EdgeType.PREREQUISITE))
        graph.add_edge(Edge(from_node_id="B", to_node_id="C", weight=0.5, type=EdgeType.PREREQUISITE))
        graph.add_edge(Edge(from_node_id="C", to_node_id="A", weight=0.5, type=EdgeType.PREREQUISITE))
        
        assert graph.path_exists("A", "C", max_hops=5) is True


# ============================================================
# SHORTEST PATH TESTS
# ============================================================


class TestShortestPath:
    """Tests for shortest_path method."""
    
    def test_shortest_path_direct_connection(self):
        """Should find direct path."""
        graph = Graph()
        
        node_a = Node(id="A", topic_name="Topic A")
        node_b = Node(id="B", topic_name="Topic B")
        
        graph.add_node(node_a)
        graph.add_node(node_b)
        graph.add_edge(Edge(from_node_id="A", to_node_id="B", weight=0.5, type=EdgeType.PREREQUISITE))
        
        path = graph.shortest_path("A", "B", max_hops=1)
        assert path == ["A", "B"]
    
    def test_shortest_path_multi_hop(self):
        """Should find path through intermediate nodes."""
        graph = Graph()
        
        # A -> B -> C
        for node_id in ["A", "B", "C"]:
            graph.add_node(Node(id=node_id, topic_name=f"Topic {node_id}"))
        
        graph.add_edge(Edge(from_node_id="A", to_node_id="B", weight=0.5, type=EdgeType.PREREQUISITE))
        graph.add_edge(Edge(from_node_id="B", to_node_id="C", weight=0.5, type=EdgeType.PREREQUISITE))
        
        path = graph.shortest_path("A", "C", max_hops=2)
        assert path == ["A", "B", "C"]
    
    def test_shortest_path_chooses_shortest(self):
        """Should choose the shortest path when multiple exist."""
        graph = Graph()
        
        # A -> B -> D (2 hops)
        # A -> C -> E -> D (3 hops)
        for node_id in ["A", "B", "C", "D", "E"]:
            graph.add_node(Node(id=node_id, topic_name=f"Topic {node_id}"))
        
        graph.add_edge(Edge(from_node_id="A", to_node_id="B", weight=0.5, type=EdgeType.PREREQUISITE))
        graph.add_edge(Edge(from_node_id="B", to_node_id="D", weight=0.5, type=EdgeType.PREREQUISITE))
        graph.add_edge(Edge(from_node_id="A", to_node_id="C", weight=0.5, type=EdgeType.PREREQUISITE))
        graph.add_edge(Edge(from_node_id="C", to_node_id="E", weight=0.5, type=EdgeType.PREREQUISITE))
        graph.add_edge(Edge(from_node_id="E", to_node_id="D", weight=0.5, type=EdgeType.PREREQUISITE))
        
        path = graph.shortest_path("A", "D", max_hops=5)
        assert path == ["A", "B", "D"]
    
    def test_shortest_path_respects_max_hops(self):
        """Should return None if path exceeds max_hops."""
        graph = Graph()
        
        # A -> B -> C -> D
        for node_id in ["A", "B", "C", "D"]:
            graph.add_node(Node(id=node_id, topic_name=f"Topic {node_id}"))
        
        graph.add_edge(Edge(from_node_id="A", to_node_id="B", weight=0.5, type=EdgeType.PREREQUISITE))
        graph.add_edge(Edge(from_node_id="B", to_node_id="C", weight=0.5, type=EdgeType.PREREQUISITE))
        graph.add_edge(Edge(from_node_id="C", to_node_id="D", weight=0.5, type=EdgeType.PREREQUISITE))
        
        path = graph.shortest_path("A", "D", max_hops=2)
        assert path is None
        
        path = graph.shortest_path("A", "D", max_hops=3)
        assert path == ["A", "B", "C", "D"]
    
    def test_shortest_path_no_connection(self):
        """Should return None if no path exists."""
        graph = Graph()
        
        node_a = Node(id="A", topic_name="Topic A")
        node_b = Node(id="B", topic_name="Topic B")
        
        graph.add_node(node_a)
        graph.add_node(node_b)
        
        path = graph.shortest_path("A", "B", max_hops=5)
        assert path is None
    
    def test_shortest_path_with_edge_type_filter(self):
        """Should only follow allowed edge types."""
        graph = Graph()
        
        # A -PREREQ-> B -DEPENDS_ON-> C
        for node_id in ["A", "B", "C"]:
            graph.add_node(Node(id=node_id, topic_name=f"Topic {node_id}"))
        
        graph.add_edge(Edge(from_node_id="A", to_node_id="B", weight=0.5, type=EdgeType.PREREQUISITE))
        graph.add_edge(Edge(from_node_id="B", to_node_id="C", weight=0.5, type=EdgeType.DEPENDS_ON))
        
        # Following only PREREQUISITE should not reach C
        path = graph.shortest_path("A", "C", max_hops=2, allowed_edge_types={EdgeType.PREREQUISITE})
        assert path is None
        
        # Following both types should reach C
        path = graph.shortest_path("A", "C", max_hops=2, allowed_edge_types={EdgeType.PREREQUISITE, EdgeType.DEPENDS_ON})
        assert path == ["A", "B", "C"]
    
    def test_shortest_path_same_node(self):
        """Should return single-node path if from and to are the same."""
        graph = Graph()
        
        node_a = Node(id="A", topic_name="Topic A")
        graph.add_node(node_a)
        
        path = graph.shortest_path("A", "A", max_hops=1)
        assert path == ["A"]
    
    def test_shortest_path_nonexistent_from_node(self):
        """Should raise error if from_node doesn't exist."""
        graph = Graph()
        node_b = Node(id="B", topic_name="Topic B")
        graph.add_node(node_b)
        
        with pytest.raises(KeyError, match="not found"):
            graph.shortest_path("X", "B", max_hops=1)
    
    def test_shortest_path_nonexistent_to_node(self):
        """Should raise error if to_node doesn't exist."""
        graph = Graph()
        node_a = Node(id="A", topic_name="Topic A")
        graph.add_node(node_a)
        
        with pytest.raises(KeyError, match="not found"):
            graph.shortest_path("A", "X", max_hops=1)
    
    def test_shortest_path_invalid_max_hops(self):
        """Should raise error if max_hops < 1."""
        graph = Graph()
        node_a = Node(id="A", topic_name="Topic A")
        graph.add_node(node_a)
        
        with pytest.raises(ValueError, match="max_hops must be >= 1"):
            graph.shortest_path("A", "A", max_hops=0)


# ============================================================
# VALID COVERAGE TESTS
# ============================================================


class TestValidCoverage:
    """Tests for is_valid_coverage method."""
    
    def test_valid_coverage_two_connected_nodes(self):
        """Should validate two connected nodes."""
        graph = Graph()
        
        node_a = Node(id="A", topic_name="Topic A")
        node_b = Node(id="B", topic_name="Topic B")
        
        graph.add_node(node_a)
        graph.add_node(node_b)
        graph.add_edge(Edge(from_node_id="A", to_node_id="B", weight=0.5, type=EdgeType.PREREQUISITE))
        
        is_valid = graph.is_valid_coverage(["A", "B"], max_hops=1, allowed_edge_types={EdgeType.PREREQUISITE})
        assert is_valid is True
    
    def test_valid_coverage_bidirectional_connection(self):
        """Should accept connection in either direction."""
        graph = Graph()
        
        # A -> B (but not B -> A)
        node_a = Node(id="A", topic_name="Topic A")
        node_b = Node(id="B", topic_name="Topic B")
        
        graph.add_node(node_a)
        graph.add_node(node_b)
        graph.add_edge(Edge(from_node_id="A", to_node_id="B", weight=0.5, type=EdgeType.PREREQUISITE))
        
        # Should be valid even if we check B -> A
        is_valid = graph.is_valid_coverage(["B", "A"], max_hops=1, allowed_edge_types={EdgeType.PREREQUISITE})
        assert is_valid is True
    
    def test_valid_coverage_multiple_nodes_connected(self):
        """Should validate multiple connected nodes."""
        graph = Graph()
        
        # A -> B -> C (all within 2 hops of each other)
        for node_id in ["A", "B", "C"]:
            graph.add_node(Node(id=node_id, topic_name=f"Topic {node_id}"))
        
        graph.add_edge(Edge(from_node_id="A", to_node_id="B", weight=0.5, type=EdgeType.PREREQUISITE))
        graph.add_edge(Edge(from_node_id="B", to_node_id="C", weight=0.5, type=EdgeType.PREREQUISITE))
        
        is_valid = graph.is_valid_coverage(["A", "B", "C"], max_hops=2, allowed_edge_types={EdgeType.PREREQUISITE})
        assert is_valid is True
    
    def test_valid_coverage_disconnected_nodes(self):
        """Should reject disconnected nodes."""
        graph = Graph()
        
        node_a = Node(id="A", topic_name="Topic A")
        node_b = Node(id="B", topic_name="Topic B")
        
        graph.add_node(node_a)
        graph.add_node(node_b)
        
        is_valid = graph.is_valid_coverage(["A", "B"], max_hops=5, allowed_edge_types={EdgeType.PREREQUISITE})
        assert is_valid is False
    
    def test_valid_coverage_nodes_too_far(self):
        """Should reject nodes beyond max_hops."""
        graph = Graph()
        
        # A -> B -> C -> D (3 hops)
        for node_id in ["A", "B", "C", "D"]:
            graph.add_node(Node(id=node_id, topic_name=f"Topic {node_id}"))
        
        graph.add_edge(Edge(from_node_id="A", to_node_id="B", weight=0.5, type=EdgeType.PREREQUISITE))
        graph.add_edge(Edge(from_node_id="B", to_node_id="C", weight=0.5, type=EdgeType.PREREQUISITE))
        graph.add_edge(Edge(from_node_id="C", to_node_id="D", weight=0.5, type=EdgeType.PREREQUISITE))
        
        # A and D are 3 hops apart
        is_valid = graph.is_valid_coverage(["A", "D"], max_hops=2, allowed_edge_types={EdgeType.PREREQUISITE})
        assert is_valid is False
        
        is_valid = graph.is_valid_coverage(["A", "D"], max_hops=3, allowed_edge_types={EdgeType.PREREQUISITE})
        assert is_valid is True
    
    def test_valid_coverage_partially_connected(self):
        """Should reject if any pair is not connected."""
        graph = Graph()
        
        # A -> B, C (isolated)
        for node_id in ["A", "B", "C"]:
            graph.add_node(Node(id=node_id, topic_name=f"Topic {node_id}"))
        
        graph.add_edge(Edge(from_node_id="A", to_node_id="B", weight=0.5, type=EdgeType.PREREQUISITE))
        
        # A and B are connected, but C is isolated
        is_valid = graph.is_valid_coverage(["A", "B", "C"], max_hops=5, allowed_edge_types={EdgeType.PREREQUISITE})
        assert is_valid is False
    
    def test_valid_coverage_respects_edge_types(self):
        """Should only consider allowed edge types."""
        graph = Graph()
        
        # A -PREREQ-> B -DEPENDS_ON-> C
        for node_id in ["A", "B", "C"]:
            graph.add_node(Node(id=node_id, topic_name=f"Topic {node_id}"))
        
        graph.add_edge(Edge(from_node_id="A", to_node_id="B", weight=0.5, type=EdgeType.PREREQUISITE))
        graph.add_edge(Edge(from_node_id="B", to_node_id="C", weight=0.5, type=EdgeType.DEPENDS_ON))
        
        # Only PREREQUISITE: A and C not connected
        is_valid = graph.is_valid_coverage(["A", "C"], max_hops=2, allowed_edge_types={EdgeType.PREREQUISITE})
        assert is_valid is False
        
        # Both types: A and C connected
        is_valid = graph.is_valid_coverage(["A", "C"], max_hops=2, allowed_edge_types={EdgeType.PREREQUISITE, EdgeType.DEPENDS_ON})
        assert is_valid is True
    
    def test_valid_coverage_single_node_error(self):
        """Should raise error if only one node provided."""
        graph = Graph()
        node_a = Node(id="A", topic_name="Topic A")
        graph.add_node(node_a)
        
        with pytest.raises(ValueError, match="must contain at least 2 nodes"):
            graph.is_valid_coverage(["A"], max_hops=1, allowed_edge_types={EdgeType.PREREQUISITE})
    
    def test_valid_coverage_empty_list_error(self):
        """Should raise error if empty list provided."""
        graph = Graph()
        
        with pytest.raises(ValueError, match="must contain at least 2 nodes"):
            graph.is_valid_coverage([], max_hops=1, allowed_edge_types={EdgeType.PREREQUISITE})
    
    def test_valid_coverage_nonexistent_node(self):
        """Should raise error if any node doesn't exist."""
        graph = Graph()
        node_a = Node(id="A", topic_name="Topic A")
        graph.add_node(node_a)
        
        with pytest.raises(KeyError, match="not found"):
            graph.is_valid_coverage(["A", "X"], max_hops=1, allowed_edge_types={EdgeType.PREREQUISITE})
    
    def test_valid_coverage_complex_graph(self):
        """Should validate coverage in complex graph."""
        graph = Graph()
        
        # Create a linear chain: A -> B -> C -> D
        for node_id in ["A", "B", "C", "D"]:
            graph.add_node(Node(id=node_id, topic_name=f"Topic {node_id}"))
        
        graph.add_edge(Edge(from_node_id="A", to_node_id="B", weight=0.5, type=EdgeType.PREREQUISITE))
        graph.add_edge(Edge(from_node_id="B", to_node_id="C", weight=0.5, type=EdgeType.PREREQUISITE))
        graph.add_edge(Edge(from_node_id="C", to_node_id="D", weight=0.5, type=EdgeType.PREREQUISITE))
        
        # A and D are 3 hops apart
        # With max_hops=2, not all pairs are within reach
        is_valid = graph.is_valid_coverage(["A", "D"], max_hops=2, allowed_edge_types={EdgeType.PREREQUISITE})
        assert is_valid is False
        
        # With max_hops=3, A can reach D
        is_valid = graph.is_valid_coverage(["A", "D"], max_hops=3, allowed_edge_types={EdgeType.PREREQUISITE})
        assert is_valid is True
        
        # Test subset that are closer together
        is_valid = graph.is_valid_coverage(["A", "B", "C"], max_hops=2, allowed_edge_types={EdgeType.PREREQUISITE})
        assert is_valid is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
