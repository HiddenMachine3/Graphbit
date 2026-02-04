"""
Phase 5: Weak Node Clustering Tests

Comprehensive unit tests for weak node detection and clustering.
"""

from datetime import datetime, timedelta
import pytest
from pydantic import ValidationError

from backend.app.domain import (
    Cluster,
    WeakNodeDetector,
    WeakNodeClusterer,
    MAX_CLUSTER_SIZE,
    Graph,
    Node,
    Edge,
    EdgeType,
    UserNodeState,
)


# ============================================================
# TEST HELPERS
# ============================================================


def create_node(node_id: str, topic_name: str = None) -> Node:
    """Helper to create Node."""
    return Node(
        id=node_id,
        topic_name=topic_name or node_id.capitalize()
    )


def create_edge(from_id: str, to_id: str, edge_type=EdgeType.PREREQUISITE) -> Edge:
    """Helper to create Edge."""
    return Edge(
        from_node_id=from_id,
        to_node_id=to_id,
        type=edge_type,
        weight=1.0
    )


def create_user_state(
    node_id: str,
    pkr: float = 0.5,
    stability: float = 5.0,
    last_reviewed: datetime = None
) -> UserNodeState:
    """Helper to create UserNodeState."""
    return UserNodeState(
        user_id="user1",
        node_id=node_id,
        proven_knowledge_rating=pkr,
        stability=stability,
        last_reviewed_at=last_reviewed or datetime.now()
    )


# ============================================================
# CLUSTER DATA STRUCTURE TESTS
# ============================================================


class TestClusterDataStructure:
    """Tests for Cluster validation."""
    
    def test_create_valid_cluster(self):
        """Should create cluster with valid fields."""
        cluster = Cluster(
            node_ids={"node1", "node2"},
            seed_node_id="node1"
        )
        
        assert cluster.node_ids == {"node1", "node2"}
        assert cluster.seed_node_id == "node1"
    
    def test_cluster_must_have_at_least_two_nodes(self):
        """Should reject single-node cluster."""
        with pytest.raises(ValidationError, match="at least 2 nodes"):
            Cluster(
                node_ids={"node1"},
                seed_node_id="node1"
            )
    
    def test_cluster_cannot_exceed_max_size(self):
        """Should reject cluster larger than MAX_CLUSTER_SIZE."""
        large_cluster = {f"node{i}" for i in range(MAX_CLUSTER_SIZE + 1)}
        
        with pytest.raises(ValidationError, match="cannot exceed"):
            Cluster(
                node_ids=large_cluster,
                seed_node_id="node0"
            )
    
    def test_seed_must_be_in_cluster(self):
        """Should reject seed not in node_ids."""
        with pytest.raises(ValidationError, match="must be in node_ids"):
            Cluster(
                node_ids={"node1", "node2"},
                seed_node_id="node3"
            )
    
    def test_cluster_at_max_size_accepted(self):
        """Should accept cluster exactly at MAX_CLUSTER_SIZE."""
        nodes = {f"node{i}" for i in range(MAX_CLUSTER_SIZE)}
        
        cluster = Cluster(
            node_ids=nodes,
            seed_node_id="node0"
        )
        
        assert len(cluster.node_ids) == MAX_CLUSTER_SIZE


# ============================================================
# WEAK NODE DETECTOR TESTS
# ============================================================


class TestWeakNodeDetector:
    """Tests for WeakNodeDetector."""
    
    def test_detect_single_weak_node(self):
        """Should identify single weak node."""
        now = datetime.now()
        old_review = now - timedelta(days=30)
        
        states = [
            create_user_state("node1", pkr=0.2, last_reviewed=old_review),
        ]
        
        importance = {"node1": 1.0}
        
        weak_nodes = WeakNodeDetector.get_weak_nodes(
            states, now, importance, weakness_threshold=0.5
        )
        
        assert weak_nodes == ["node1"]
    
    def test_detect_multiple_weak_nodes(self):
        """Should identify multiple weak nodes."""
        now = datetime.now()
        old_review = now - timedelta(days=30)
        
        states = [
            create_user_state("node1", pkr=0.1, last_reviewed=old_review),
            create_user_state("node2", pkr=0.2, last_reviewed=old_review),
            create_user_state("node3", pkr=0.9, last_reviewed=now),  # Strong
        ]
        
        importance = {"node1": 1.0, "node2": 1.0, "node3": 1.0}
        
        weak_nodes = WeakNodeDetector.get_weak_nodes(
            states, now, importance, weakness_threshold=0.3
        )
        
        assert len(weak_nodes) == 2
        assert "node1" in weak_nodes
        assert "node2" in weak_nodes
        assert "node3" not in weak_nodes
    
    def test_no_weak_nodes_when_all_strong(self):
        """Should return empty list when no nodes are weak."""
        now = datetime.now()
        
        states = [
            create_user_state("node1", pkr=0.9, last_reviewed=now),
            create_user_state("node2", pkr=0.95, last_reviewed=now),
        ]
        
        importance = {"node1": 1.0, "node2": 1.0}
        
        weak_nodes = WeakNodeDetector.get_weak_nodes(
            states, now, importance, weakness_threshold=0.2
        )
        
        assert weak_nodes == []
    
    def test_all_nodes_weak_when_threshold_low(self):
        """Should identify all nodes when threshold is very low."""
        now = datetime.now()
        
        states = [
            create_user_state("node1", pkr=0.5, last_reviewed=now),
            create_user_state("node2", pkr=0.6, last_reviewed=now),
        ]
        
        importance = {"node1": 1.0, "node2": 1.0}
        
        weak_nodes = WeakNodeDetector.get_weak_nodes(
            states, now, importance, weakness_threshold=0.0
        )
        
        assert len(weak_nodes) == 2
    
    def test_importance_affects_weakness(self):
        """Should weight weakness by importance."""
        now = datetime.now()
        old_review = now - timedelta(days=30)
        
        states = [
            create_user_state("important", pkr=0.4, last_reviewed=old_review),
            create_user_state("unimportant", pkr=0.4, last_reviewed=old_review),
        ]
        
        importance = {"important": 5.0, "unimportant": 0.5}
        
        weak_nodes = WeakNodeDetector.get_weak_nodes(
            states, now, importance, weakness_threshold=0.85
        )
        
        # High importance amplifies weakness
        assert "important" in weak_nodes
        assert "unimportant" not in weak_nodes
    
    def test_default_importance_used_when_missing(self):
        """Should use default importance of 1.0 when not specified."""
        now = datetime.now()
        old_review = now - timedelta(days=30)
        
        states = [
            create_user_state("node1", pkr=0.2, last_reviewed=old_review),
        ]
        
        # Empty importance lookup
        importance = {}
        
        weak_nodes = WeakNodeDetector.get_weak_nodes(
            states, now, importance, weakness_threshold=0.5
        )
        
        assert "node1" in weak_nodes
    
    def test_deterministic_ordering(self):
        """Should return nodes in sorted order."""
        now = datetime.now()
        old_review = now - timedelta(days=30)
        
        states = [
            create_user_state("zebra", pkr=0.1, last_reviewed=old_review),
            create_user_state("apple", pkr=0.1, last_reviewed=old_review),
            create_user_state("banana", pkr=0.1, last_reviewed=old_review),
        ]
        
        importance = {"zebra": 1.0, "apple": 1.0, "banana": 1.0}
        
        weak_nodes = WeakNodeDetector.get_weak_nodes(
            states, now, importance, weakness_threshold=0.5
        )
        
        assert weak_nodes == ["apple", "banana", "zebra"]


# ============================================================
# WEAK NODE CLUSTERER TESTS
# ============================================================


class TestWeakNodeClusterer:
    """Tests for WeakNodeClusterer."""
    
    def test_create_clusterer(self):
        """Should create clusterer with graph and constraints."""
        graph = Graph()
        
        clusterer = WeakNodeClusterer(
            graph=graph,
            max_hops=2,
            allowed_edge_types={EdgeType.PREREQUISITE}
        )
        
        assert clusterer.graph == graph
        assert clusterer.max_hops == 2
        assert clusterer.allowed_edge_types == {EdgeType.PREREQUISITE}
    
    def test_generate_cluster_from_two_connected_nodes(self):
        """Should create cluster from two connected weak nodes."""
        graph = Graph()
        graph.add_node(create_node("python"))
        graph.add_node(create_node("variables"))
        graph.add_edge(create_edge("python", "variables"))
        
        clusterer = WeakNodeClusterer(graph, max_hops=2)
        
        weak_nodes = ["python", "variables"]
        clusters = clusterer.generate_clusters(weak_nodes)
        
        assert len(clusters) == 1
        assert clusters[0].node_ids == {"python", "variables"}
        assert clusters[0].seed_node_id in ["python", "variables"]
    
    def test_no_clusters_from_single_weak_node(self):
        """Should not create cluster from single weak node."""
        graph = Graph()
        graph.add_node(create_node("python"))
        
        clusterer = WeakNodeClusterer(graph, max_hops=2)
        
        weak_nodes = ["python"]
        clusters = clusterer.generate_clusters(weak_nodes)
        
        assert len(clusters) == 0
    
    def test_no_clusters_from_disconnected_nodes(self):
        """Should not create clusters from disconnected weak nodes."""
        graph = Graph()
        graph.add_node(create_node("python"))
        graph.add_node(create_node("java"))
        # No edge between them
        
        clusterer = WeakNodeClusterer(graph, max_hops=2)
        
        weak_nodes = ["python", "java"]
        clusters = clusterer.generate_clusters(weak_nodes)
        
        assert len(clusters) == 0
    
    def test_cluster_respects_max_hops(self):
        """Should only include nodes within max_hops."""
        graph = Graph()
        graph.add_node(create_node("a"))
        graph.add_node(create_node("b"))
        graph.add_node(create_node("c"))
        graph.add_edge(create_edge("a", "b"))
        graph.add_edge(create_edge("b", "c"))
        
        # With max_hops=1, a and c are not reachable
        clusterer = WeakNodeClusterer(graph, max_hops=1)
        
        weak_nodes = ["a", "b", "c"]
        clusters = clusterer.generate_clusters(weak_nodes)
        
        # Should create two clusters: (a,b) and (b,c)
        assert len(clusters) == 2
        
        # No cluster should contain both a and c
        for cluster in clusters:
            assert not ("a" in cluster.node_ids and "c" in cluster.node_ids)
    
    def test_cluster_respects_edge_types(self):
        """Should only traverse allowed edge types."""
        graph = Graph()
        graph.add_node(create_node("a"))
        graph.add_node(create_node("b"))
        graph.add_node(create_node("c"))
        graph.add_edge(create_edge("a", "b", EdgeType.PREREQUISITE))
        graph.add_edge(create_edge("b", "c", EdgeType.APPLIED_WITH))
        
        # Only allow PREREQUISITE edges
        clusterer = WeakNodeClusterer(
            graph,
            max_hops=2,
            allowed_edge_types={EdgeType.PREREQUISITE}
        )
        
        weak_nodes = ["a", "b", "c"]
        clusters = clusterer.generate_clusters(weak_nodes)
        
        # Should only cluster a and b (connected by PREREQUISITE)
        # b and c should not cluster (connected by APPLIED_WITH)
        assert any(
            cluster.node_ids == {"a", "b"}
            for cluster in clusters
        )
        
        assert not any(
            "c" in cluster.node_ids and "b" in cluster.node_ids
            for cluster in clusters
        )
    
    def test_deduplicates_identical_clusters(self):
        """Should not create duplicate clusters with same nodes."""
        graph = Graph()
        graph.add_node(create_node("a"))
        graph.add_node(create_node("b"))
        graph.add_edge(create_edge("a", "b"))
        graph.add_edge(create_edge("b", "a"))  # Bidirectional
        
        clusterer = WeakNodeClusterer(graph, max_hops=1)
        
        weak_nodes = ["a", "b"]
        clusters = clusterer.generate_clusters(weak_nodes)
        
        # Should only create one cluster, not two
        assert len(clusters) == 1
        assert clusters[0].node_ids == {"a", "b"}
    
    def test_enforces_max_cluster_size(self):
        """Should limit cluster size to MAX_CLUSTER_SIZE."""
        graph = Graph()
        # Create chain: a -> b -> c -> d
        for node_id in ["a", "b", "c", "d"]:
            graph.add_node(create_node(node_id))
        
        graph.add_edge(create_edge("a", "b"))
        graph.add_edge(create_edge("b", "c"))
        graph.add_edge(create_edge("c", "d"))
        
        clusterer = WeakNodeClusterer(graph, max_hops=10)
        
        weak_nodes = ["a", "b", "c", "d"]
        clusters = clusterer.generate_clusters(weak_nodes)
        
        # All clusters should respect max size
        for cluster in clusters:
            assert len(cluster.node_ids) <= MAX_CLUSTER_SIZE
    
    def test_empty_weak_nodes_returns_empty_clusters(self):
        """Should return empty list when no weak nodes provided."""
        graph = Graph()
        graph.add_node(create_node("a"))
        
        clusterer = WeakNodeClusterer(graph, max_hops=2)
        
        clusters = clusterer.generate_clusters([])
        
        assert clusters == []
    
    def test_deterministic_cluster_generation(self):
        """Should generate same clusters given same input."""
        graph = Graph()
        graph.add_node(create_node("a"))
        graph.add_node(create_node("b"))
        graph.add_node(create_node("c"))
        graph.add_edge(create_edge("a", "b"))
        graph.add_edge(create_edge("b", "c"))
        
        clusterer = WeakNodeClusterer(graph, max_hops=2)
        
        weak_nodes = ["a", "b", "c"]
        
        clusters1 = clusterer.generate_clusters(weak_nodes)
        clusters2 = clusterer.generate_clusters(weak_nodes)
        
        assert len(clusters1) == len(clusters2)
        
        # Same node sets (order doesn't matter)
        for c1, c2 in zip(clusters1, clusters2):
            assert c1.node_ids == c2.node_ids


# ============================================================
# INTEGRATION TESTS
# ============================================================


class TestWeakNodeClusteringIntegration:
    """Integration tests combining detection and clustering."""
    
    def test_full_pipeline_simple_graph(self):
        """Should detect weak nodes and cluster them."""
        # Build graph
        graph = Graph()
        graph.add_node(create_node("python"))
        graph.add_node(create_node("variables"))
        graph.add_node(create_node("functions"))
        graph.add_edge(create_edge("python", "variables"))
        graph.add_edge(create_edge("variables", "functions"))
        
        # Create user states (all weak)
        now = datetime.now()
        old_review = now - timedelta(days=30)
        
        states = [
            create_user_state("python", pkr=0.2, last_reviewed=old_review),
            create_user_state("variables", pkr=0.3, last_reviewed=old_review),
            create_user_state("functions", pkr=0.1, last_reviewed=old_review),
        ]
        
        importance = {
            "python": 1.0,
            "variables": 1.0,
            "functions": 1.0,
        }
        
        # Detect weak nodes
        weak_nodes = WeakNodeDetector.get_weak_nodes(
            states, now, importance, weakness_threshold=0.5
        )
        
        assert len(weak_nodes) == 3
        
        # Generate clusters
        clusterer = WeakNodeClusterer(graph, max_hops=2)
        clusters = clusterer.generate_clusters(weak_nodes)
        
        # Should create at least one cluster
        assert len(clusters) > 0
        
        # All clusters should be valid
        for cluster in clusters:
            assert len(cluster.node_ids) >= 2
            assert len(cluster.node_ids) <= MAX_CLUSTER_SIZE
            assert cluster.seed_node_id in cluster.node_ids
    
    def test_mixed_weak_and_strong_nodes(self):
        """Should only cluster weak nodes, not strong ones."""
        graph = Graph()
        graph.add_node(create_node("weak1"))
        graph.add_node(create_node("strong"))
        graph.add_node(create_node("weak2"))
        graph.add_edge(create_edge("weak1", "strong"))
        graph.add_edge(create_edge("strong", "weak2"))
        
        now = datetime.now()
        old_review = now - timedelta(days=30)
        
        states = [
            create_user_state("weak1", pkr=0.1, last_reviewed=old_review),
            create_user_state("strong", pkr=0.9, last_reviewed=now),
            create_user_state("weak2", pkr=0.2, last_reviewed=old_review),
        ]
        
        importance = {"weak1": 1.0, "strong": 1.0, "weak2": 1.0}
        
        weak_nodes = WeakNodeDetector.get_weak_nodes(
            states, now, importance, weakness_threshold=0.3
        )
        
        assert "strong" not in weak_nodes
        assert len(weak_nodes) == 2
        
        # Try to cluster (should fail - weak nodes not connected)
        clusterer = WeakNodeClusterer(graph, max_hops=1)
        clusters = clusterer.generate_clusters(weak_nodes)
        
        # No cluster should contain the strong node
        for cluster in clusters:
            assert "strong" not in cluster.node_ids
    
    def test_large_graph_multiple_clusters(self):
        """Should create multiple distinct clusters from larger graph."""
        graph = Graph()
        
        # Cluster 1: python basics
        graph.add_node(create_node("python"))
        graph.add_node(create_node("variables"))
        graph.add_edge(create_edge("python", "variables"))
        
        # Cluster 2: advanced concepts (disconnected)
        graph.add_node(create_node("classes"))
        graph.add_node(create_node("inheritance"))
        graph.add_edge(create_edge("classes", "inheritance"))
        
        # All weak
        now = datetime.now()
        old_review = now - timedelta(days=30)
        
        states = [
            create_user_state("python", pkr=0.1, last_reviewed=old_review),
            create_user_state("variables", pkr=0.2, last_reviewed=old_review),
            create_user_state("classes", pkr=0.15, last_reviewed=old_review),
            create_user_state("inheritance", pkr=0.25, last_reviewed=old_review),
        ]
        
        importance = {node: 1.0 for node in ["python", "variables", "classes", "inheritance"]}
        
        weak_nodes = WeakNodeDetector.get_weak_nodes(
            states, now, importance, weakness_threshold=0.5
        )
        
        clusterer = WeakNodeClusterer(graph, max_hops=2)
        clusters = clusterer.generate_clusters(weak_nodes)
        
        # Should create 2 clusters (one for each disconnected component)
        assert len(clusters) == 2
        
        # Clusters should not overlap
        all_nodes = set()
        for cluster in clusters:
            assert cluster.node_ids.isdisjoint(all_nodes)
            all_nodes.update(cluster.node_ids)


# ============================================================
# EDGE CASE TESTS
# ============================================================


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""
    
    def test_cluster_with_nonexistent_node_rejected(self):
        """Should handle nonexistent nodes gracefully."""
        graph = Graph()
        graph.add_node(create_node("exists"))
        
        clusterer = WeakNodeClusterer(graph, max_hops=2)
        
        # Include nonexistent node
        weak_nodes = ["exists", "nonexistent"]
        clusters = clusterer.generate_clusters(weak_nodes)
        
        # Should not crash, but may produce no valid clusters
        assert isinstance(clusters, list)
    
    def test_self_loop_does_not_create_cluster(self):
        """Should not create cluster from node with self-loop."""
        graph = Graph()
        graph.add_node(create_node("a"))
        
        # Self loop (if allowed by Edge validation)
        try:
            graph.add_edge(create_edge("a", "a"))
        except:
            pass  # Self loops might be invalid
        
        clusterer = WeakNodeClusterer(graph, max_hops=2)
        
        weak_nodes = ["a"]
        clusters = clusterer.generate_clusters(weak_nodes)
        
        assert len(clusters) == 0
    
    def test_very_high_weakness_threshold(self):
        """Should return no weak nodes with impossibly high threshold."""
        now = datetime.now()
        
        states = [
            create_user_state("node1", pkr=0.0, last_reviewed=now - timedelta(days=365)),
        ]
        
        importance = {"node1": 1.0}
        
        weak_nodes = WeakNodeDetector.get_weak_nodes(
            states, now, importance, weakness_threshold=100.0
        )
        
        assert weak_nodes == []
    
    def test_zero_weakness_threshold(self):
        """Should return all nodes with zero threshold."""
        now = datetime.now()
        
        states = [
            create_user_state("node1", pkr=1.0, last_reviewed=now),
            create_user_state("node2", pkr=0.99, last_reviewed=now),
        ]
        
        importance = {"node1": 1.0, "node2": 1.0}
        
        weak_nodes = WeakNodeDetector.get_weak_nodes(
            states, now, importance, weakness_threshold=0.0
        )
        
        assert len(weak_nodes) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
