"""Graph model and reasoning operations."""

from collections import deque
from typing import Optional

from pydantic import BaseModel, Field

from .enums import EdgeType
from .node import Node
from .edge import Edge


class Graph(BaseModel):
    """
    Represents a knowledge graph containing nodes and their relationships.
    
    Manages the collection of nodes and edges, ensuring referential integrity.
    Provides reasoning operations for path finding and coverage validation.
    """
    
    nodes: dict[str, Node] = Field(default_factory=dict)
    edges: list[Edge] = Field(default_factory=list)
    
    def add_node(self, node: Node) -> None:
        """
        Add a node to the graph.
        
        Args:
            node: The node to add
            
        Raises:
            ValueError: If a node with this ID already exists
        """
        if node.id in self.nodes:
            raise ValueError(f"Node with id '{node.id}' already exists")
        self.nodes[node.id] = node
    
    def remove_node(self, node_id: str) -> None:
        """
        Remove a node from the graph.
        
        Also removes all edges connected to this node.
        
        Args:
            node_id: ID of the node to remove
            
        Raises:
            KeyError: If node doesn't exist
        """
        if node_id not in self.nodes:
            raise KeyError(f"Node with id '{node_id}' not found")
        
        # Remove the node
        del self.nodes[node_id]
        
        # Remove all edges connected to this node
        self.edges = [
            edge for edge in self.edges
            if edge.from_node_id != node_id and edge.to_node_id != node_id
        ]
    
    def add_edge(self, edge: Edge) -> None:
        """
        Add an edge to the graph.
        
        Args:
            edge: The edge to add
            
        Raises:
            ValueError: If either referenced node doesn't exist
        """
        if edge.from_node_id not in self.nodes:
            raise ValueError(f"from_node_id '{edge.from_node_id}' not found in graph")
        if edge.to_node_id not in self.nodes:
            raise ValueError(f"to_node_id '{edge.to_node_id}' not found in graph")
        
        self.edges.append(edge)
    
    def remove_edge(self, from_node_id: str, to_node_id: str) -> None:
        """
        Remove an edge from the graph.
        
        Args:
            from_node_id: Source node ID
            to_node_id: Target node ID
            
        Raises:
            ValueError: If no such edge exists
        """
        original_length = len(self.edges)
        self.edges = [
            edge for edge in self.edges
            if not (edge.from_node_id == from_node_id and edge.to_node_id == to_node_id)
        ]
        
        if len(self.edges) == original_length:
            raise ValueError(
                f"No edge found from '{from_node_id}' to '{to_node_id}'"
            )
    
    # ============================================================
    # PHASE 2: Knowledge Graph Reasoning Operations
    # ============================================================
    
    def get_outgoing_neighbors(self, node_id: str) -> list[str]:
        """
        Get IDs of nodes directly reachable from node_id via outgoing edges.
        
        Args:
            node_id: The node to find outgoing neighbors for
            
        Returns:
            List of node IDs reachable via outgoing edges
            
        Raises:
            KeyError: If node doesn't exist
        """
        if node_id not in self.nodes:
            raise KeyError(f"Node with id '{node_id}' not found")
        
        neighbors = []
        for edge in self.edges:
            if edge.from_node_id == node_id:
                neighbors.append(edge.to_node_id)
        
        return neighbors
    
    def get_incoming_neighbors(self, node_id: str) -> list[str]:
        """
        Get IDs of nodes that have edges pointing to node_id.
        
        Args:
            node_id: The node to find incoming neighbors for
            
        Returns:
            List of node IDs that point to this node
            
        Raises:
            KeyError: If node doesn't exist
        """
        if node_id not in self.nodes:
            raise KeyError(f"Node with id '{node_id}' not found")
        
        neighbors = []
        for edge in self.edges:
            if edge.to_node_id == node_id:
                neighbors.append(edge.from_node_id)
        
        return neighbors
    
    def get_neighbors_by_edge_type(
        self, 
        node_id: str, 
        allowed_edge_types: set[EdgeType]
    ) -> list[str]:
        """
        Get outgoing neighbors filtered by edge type.
        
        Args:
            node_id: The node to find neighbors for
            allowed_edge_types: Set of edge types to follow
            
        Returns:
            List of node IDs reachable via allowed edge types
            
        Raises:
            KeyError: If node doesn't exist
        """
        if node_id not in self.nodes:
            raise KeyError(f"Node with id '{node_id}' not found")
        
        neighbors = []
        for edge in self.edges:
            if edge.from_node_id == node_id and edge.type in allowed_edge_types:
                neighbors.append(edge.to_node_id)
        
        return neighbors
    
    def path_exists(
        self,
        from_node_id: str,
        to_node_id: str,
        max_hops: int,
        allowed_edge_types: Optional[set[EdgeType]] = None
    ) -> bool:
        """
        Check if a path exists between two nodes within hop limit.
        
        Args:
            from_node_id: Starting node ID
            to_node_id: Target node ID
            max_hops: Maximum number of hops allowed (must be >= 1)
            allowed_edge_types: Optional set of edge types to follow
            
        Returns:
            True if path exists within max_hops, False otherwise
            
        Raises:
            KeyError: If either node doesn't exist
            ValueError: If max_hops < 1
        """
        if from_node_id not in self.nodes:
            raise KeyError(f"Node with id '{from_node_id}' not found")
        if to_node_id not in self.nodes:
            raise KeyError(f"Node with id '{to_node_id}' not found")
        if max_hops < 1:
            raise ValueError(f"max_hops must be >= 1, got {max_hops}")
        
        # BFS with hop limit
        queue: deque = deque([(from_node_id, 0)])
        visited: set[str] = {from_node_id}
        
        while queue:
            current_node, hops = queue.popleft()
            
            # Check if we reached the target
            if current_node == to_node_id:
                return True
            
            # Don't expand beyond max_hops
            if hops >= max_hops:
                continue
            
            # Get neighbors based on edge type filter
            if allowed_edge_types is None:
                neighbors = self.get_outgoing_neighbors(current_node)
            else:
                neighbors = self.get_neighbors_by_edge_type(current_node, allowed_edge_types)
            
            # Explore unvisited neighbors
            for neighbor in neighbors:
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, hops + 1))
        
        return False
    
    def shortest_path(
        self,
        from_node_id: str,
        to_node_id: str,
        max_hops: int,
        allowed_edge_types: Optional[set[EdgeType]] = None
    ) -> Optional[list[str]]:
        """
        Find the shortest path between two nodes within hop limit.
        
        Args:
            from_node_id: Starting node ID
            to_node_id: Target node ID
            max_hops: Maximum number of hops allowed (must be >= 1)
            allowed_edge_types: Optional set of edge types to follow
            
        Returns:
            List of node IDs forming the path (including start and end),
            or None if no path exists within max_hops
            
        Raises:
            KeyError: If either node doesn't exist
            ValueError: If max_hops < 1
        """
        if from_node_id not in self.nodes:
            raise KeyError(f"Node with id '{from_node_id}' not found")
        if to_node_id not in self.nodes:
            raise KeyError(f"Node with id '{to_node_id}' not found")
        if max_hops < 1:
            raise ValueError(f"max_hops must be >= 1, got {max_hops}")
        
        # BFS with path tracking
        queue: deque = deque([([from_node_id], 0)])
        visited: set[str] = {from_node_id}
        
        while queue:
            path, hops = queue.popleft()
            current_node = path[-1]
            
            # Check if we reached the target
            if current_node == to_node_id:
                return path
            
            # Don't expand beyond max_hops
            if hops >= max_hops:
                continue
            
            # Get neighbors based on edge type filter
            if allowed_edge_types is None:
                neighbors = self.get_outgoing_neighbors(current_node)
            else:
                neighbors = self.get_neighbors_by_edge_type(current_node, allowed_edge_types)
            
            # Explore unvisited neighbors
            for neighbor in neighbors:
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((path + [neighbor], hops + 1))
        
        return None
    
    def is_valid_coverage(
        self,
        node_ids: list[str],
        max_hops: int,
        allowed_edge_types: set[EdgeType]
    ) -> bool:
        """
        Check if a set of nodes forms valid question coverage.
        
        Valid coverage requires all pairs of nodes to be connected
        by some path within max_hops using allowed edge types.
        
        Args:
            node_ids: List of node IDs to validate (must have at least 2)
            max_hops: Maximum hops allowed between any pair
            allowed_edge_types: Set of edge types to follow
            
        Returns:
            True if all pairs are connected within max_hops, False otherwise
            
        Raises:
            ValueError: If node_ids has fewer than 2 nodes
            KeyError: If any node doesn't exist
        """
        if len(node_ids) < 2:
            raise ValueError("node_ids must contain at least 2 nodes")
        
        # Verify all nodes exist
        for node_id in node_ids:
            if node_id not in self.nodes:
                raise KeyError(f"Node with id '{node_id}' not found")
        
        # Check all pairs are connected
        for i, node_a in enumerate(node_ids):
            for node_b in node_ids[i+1:]:
                # Check path in both directions
                if not self.path_exists(node_a, node_b, max_hops, allowed_edge_types) and \
                   not self.path_exists(node_b, node_a, max_hops, allowed_edge_types):
                    return False
        
        return True
