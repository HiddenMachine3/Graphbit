"""
Phase 5: Weak Node Clustering

Identifies weak knowledge nodes and groups them into coherent clusters
for targeted learning.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, field_validator, model_validator

from .enums import EdgeType
from .user_knowledge import UserNodeState
from .graph import Graph


# ============================================================
# CONSTANTS
# ============================================================

MAX_CLUSTER_SIZE = 3


# ============================================================
# CLUSTER DATA STRUCTURE
# ============================================================


class Cluster(BaseModel):
    """Represents a cluster of related knowledge nodes.
    
    A cluster groups related weak nodes for focused learning.
    All nodes must be graph-valid (connected within max_hops).
    """
    
    node_ids: set[str]
    seed_node_id: str
    
    @field_validator('node_ids')
    @classmethod
    def validate_cluster_size(cls, v: set[str]) -> set[str]:
        """Validate cluster size is within bounds."""
        if len(v) < 2:
            raise ValueError("Cluster must contain at least 2 nodes")
        if len(v) > MAX_CLUSTER_SIZE:
            raise ValueError(f"Cluster cannot exceed {MAX_CLUSTER_SIZE} nodes")
        return v
    
    @model_validator(mode='after')
    def validate_seed_in_cluster(self) -> 'Cluster':
        """Validate seed node is in the cluster."""
        if self.seed_node_id not in self.node_ids:
            raise ValueError("seed_node_id must be in node_ids")
        return self


# ============================================================
# WEAK NODE DETECTOR
# ============================================================


class WeakNodeDetector:
    """Identifies weak knowledge nodes for a user.
    
    Uses UserNodeState weakness scores to determine which nodes
    need attention based on a configurable threshold.
    """
    
    @staticmethod
    def get_weak_nodes(
        user_node_states: list[UserNodeState],
        now: datetime,
        importance_lookup: dict[str, float],
        weakness_threshold: float
    ) -> list[str]:
        """Identify weak nodes based on weakness threshold.
        
        Args:
            user_node_states: User's knowledge states for nodes
            now: Current timestamp for forgetting calculations
            importance_lookup: Node importance values
            weakness_threshold: Minimum weakness score to be considered weak
        
        Returns:
            Sorted list of weak node IDs (deterministic ordering)
        """
        weak_nodes = []
        
        for state in user_node_states:
            # Get importance, default to 1.0 if not specified
            importance = importance_lookup.get(state.node_id, 1.0)
            
            # Calculate weakness score
            weakness = state.weakness_score(now=now, importance=importance)
            
            # Check if node meets weakness threshold
            if weakness >= weakness_threshold:
                weak_nodes.append(state.node_id)
        
        # Return sorted for deterministic ordering
        return sorted(weak_nodes)


# ============================================================
# WEAK NODE CLUSTERER
# ============================================================


class WeakNodeClusterer:
    """Generates clusters of related weak nodes using graph reasoning.
    
    Expands weak nodes into small, coherent clusters by traversing
    the knowledge graph within specified constraints.
    """
    
    def __init__(
        self,
        graph: Graph,
        max_hops: int,
        allowed_edge_types: Optional[set[EdgeType]] = None
    ):
        """Initialize clusterer with graph and traversal constraints.
        
        Args:
            graph: Knowledge graph for navigation
            max_hops: Maximum hops between nodes in a cluster
            allowed_edge_types: Edge types to traverse (None = all types)
        """
        self.graph = graph
        self.max_hops = max_hops
        self.allowed_edge_types = allowed_edge_types
    
    def generate_clusters(self, weak_node_ids: list[str]) -> list[Cluster]:
        """Generate clusters from weak nodes.
        
        Algorithm:
        1. For each weak node (seed):
           - Find reachable weak neighbors within max_hops
           - Build cluster with seed + neighbors
           - Validate using graph.is_valid_coverage()
        2. Deduplicate clusters with identical node sets
        3. Return deterministically ordered clusters
        
        Args:
            weak_node_ids: List of weak node IDs to cluster
        
        Returns:
            List of valid clusters, sorted by seed node ID
        """
        if not weak_node_ids:
            return []
        
        weak_node_set = set(weak_node_ids)
        clusters = []
        seen_clusters = set()  # Track unique node combinations
        
        # Try each weak node as a seed
        for seed_node_id in sorted(weak_node_ids):  # Deterministic order
            # Find reachable weak neighbors
            cluster_nodes = self._expand_cluster(seed_node_id, weak_node_set)
            
            # Skip if cluster is too small
            if len(cluster_nodes) < 2:
                continue
            
            # Limit cluster size
            if len(cluster_nodes) > MAX_CLUSTER_SIZE:
                cluster_nodes = self._trim_cluster(cluster_nodes, seed_node_id)
            
            # Create frozen set for deduplication
            cluster_key = frozenset(cluster_nodes)
            
            # Skip if we've seen this exact cluster
            if cluster_key in seen_clusters:
                continue
            
            # Validate cluster coverage
            if not self._is_valid_cluster(cluster_nodes):
                continue
            
            # Create and add cluster
            cluster = Cluster(
                node_ids=cluster_nodes,
                seed_node_id=seed_node_id
            )
            clusters.append(cluster)
            seen_clusters.add(cluster_key)
        
        return clusters
    
    def _expand_cluster(
        self,
        seed_node_id: str,
        weak_node_set: set[str]
    ) -> set[str]:
        """Expand seed node to include reachable weak neighbors.
        
        Args:
            seed_node_id: Starting node for expansion
            weak_node_set: Set of all weak nodes
        
        Returns:
            Set of node IDs in the cluster
        """
        cluster_nodes = {seed_node_id}
        
        # Validate seed exists in graph
        if seed_node_id not in self.graph.nodes:
            return cluster_nodes
        
        # Find all weak nodes reachable within max_hops
        for candidate_id in weak_node_set:
            if candidate_id == seed_node_id:
                continue
            
            # Skip if candidate doesn't exist in graph
            if candidate_id not in self.graph.nodes:
                continue
            
            # Check if path exists within constraints
            try:
                if self.graph.path_exists(
                    seed_node_id,
                    candidate_id,
                    max_hops=self.max_hops,
                    allowed_edge_types=self.allowed_edge_types
                ):
                    cluster_nodes.add(candidate_id)
            except KeyError:
                # Node doesn't exist, skip
                continue
        
        return cluster_nodes
    
    def _trim_cluster(
        self,
        cluster_nodes: set[str],
        seed_node_id: str
    ) -> set[str]:
        """Trim cluster to maximum size, keeping seed and closest nodes.
        
        Args:
            cluster_nodes: Full cluster node set
            seed_node_id: Seed node (must be kept)
        
        Returns:
            Trimmed cluster node set
        """
        # Keep seed
        trimmed = {seed_node_id}
        
        # Sort other nodes by shortest path length from seed
        other_nodes = sorted(cluster_nodes - {seed_node_id})
        
        # Add nodes until we hit size limit
        for node_id in other_nodes:
            if len(trimmed) >= MAX_CLUSTER_SIZE:
                break
            
            # Find shortest path to seed
            path = self.graph.shortest_path(
                seed_node_id,
                node_id,
                max_hops=self.max_hops,
                allowed_edge_types=self.allowed_edge_types
            )
            
            # Add if path exists and we have room
            if path:
                trimmed.add(node_id)
        
        return trimmed
    
    def _is_valid_cluster(self, cluster_nodes: set[str]) -> bool:
        """Validate that cluster nodes form valid coverage.
        
        Args:
            cluster_nodes: Nodes to validate
        
        Returns:
            True if cluster is graph-valid
        """
        if len(cluster_nodes) < 2:
            return False
        
        try:
            return self.graph.is_valid_coverage(
                list(cluster_nodes),
                max_hops=self.max_hops,
                allowed_edge_types=self.allowed_edge_types
            )
        except (KeyError, ValueError):
            return False
