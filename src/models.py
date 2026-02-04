"""
Core domain models for graph-based active recall system.
Phase 1: Domain entities, validation rules, and safe update logic only.
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import Optional
from collections import deque
import math

from pydantic import BaseModel, Field, field_validator, model_validator


# ============================================================
# ENUMS
# ============================================================


class EdgeType(str, Enum):
    """Types of relationships between knowledge nodes."""
    PREREQUISITE = "PREREQUISITE"
    DEPENDS_ON = "DEPENDS_ON"
    APPLIED_WITH = "APPLIED_WITH"
    SUBCONCEPT_OF = "SUBCONCEPT_OF"


class QuestionType(str, Enum):
    """Types of active recall questions."""
    FLASHCARD = "FLASHCARD"
    CLOZE = "CLOZE"
    MCQ = "MCQ"
    OPEN = "OPEN"


class KnowledgeType(str, Enum):
    """Categories of knowledge being tested."""
    FACT = "FACT"
    CONCEPT = "CONCEPT"
    PROCEDURE = "PROCEDURE"


# ============================================================
# NODE
# ============================================================


class Node(BaseModel):
    """
    Represents a single unit of knowledge (concept, fact, skill).
    
    Tracks both proven (system-measured) and user-estimated mastery,
    along with importance, relevance, and engagement metrics.
    """
    
    id: str = Field(..., min_length=1)
    topic_name: str = Field(..., min_length=1)
    proven_knowledge_rating: float = Field(default=0.0, ge=0.0, le=1.0)
    user_estimated_knowledge_rating: float = Field(default=0.0, ge=0.0, le=1.0)
    importance: float = Field(default=0.0, ge=0.0)
    relevance: float = Field(default=0.0, ge=0.0)
    view_frequency: int = Field(default=0, ge=0)
    
    def update_proven_rating(self, new_rating: float) -> None:
        """
        Safely update the proven knowledge rating.
        
        Args:
            new_rating: New rating value (must be between 0.0 and 1.0)
            
        Raises:
            ValueError: If rating is outside [0, 1] range
        """
        if not 0.0 <= new_rating <= 1.0:
            raise ValueError(f"Rating must be between 0.0 and 1.0, got {new_rating}")
        self.proven_knowledge_rating = new_rating
    
    def update_user_estimated_rating(self, new_rating: float) -> None:
        """
        Safely update the user-estimated knowledge rating.
        
        Args:
            new_rating: New rating value (must be between 0.0 and 1.0)
            
        Raises:
            ValueError: If rating is outside [0, 1] range
        """
        if not 0.0 <= new_rating <= 1.0:
            raise ValueError(f"Rating must be between 0.0 and 1.0, got {new_rating}")
        self.user_estimated_knowledge_rating = new_rating
    
    def increment_view_frequency(self) -> None:
        """Increment the view frequency counter by 1."""
        self.view_frequency += 1


# ============================================================
# EDGE
# ============================================================


class Edge(BaseModel):
    """
    Represents a directed relationship between two knowledge nodes.
    
    Defines how nodes relate to each other in the knowledge graph,
    with a weight indicating the strength of the relationship.
    """
    
    from_node_id: str = Field(..., min_length=1)
    to_node_id: str = Field(..., min_length=1)
    weight: float = Field(..., ge=0.0, le=1.0)
    type: EdgeType
    
    @model_validator(mode='after')
    def validate_different_nodes(self) -> 'Edge':
        """Ensure edge connects two different nodes."""
        if self.from_node_id == self.to_node_id:
            raise ValueError("from_node_id and to_node_id must be different")
        return self


# ============================================================
# GRAPH
# ============================================================


class Graph(BaseModel):
    """
    Represents a knowledge graph containing nodes and their relationships.
    
    Manages the collection of nodes and edges, ensuring referential integrity.
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


# ============================================================
# QUESTION
# ============================================================


class QuestionMetadata(BaseModel):
    """Metadata associated with a question."""
    
    created_by: str = Field(..., min_length=1)
    created_at: datetime
    importance: float = Field(default=0.0, ge=0.0)
    hits: int = Field(default=0, ge=0)
    misses: int = Field(default=0, ge=0)


class Question(BaseModel):
    """
    Represents an active recall question.
    
    Questions test knowledge of one or more related nodes in the graph.
    Tracks performance through hits and misses.
    """
    
    id: str = Field(..., min_length=1)
    text: str = Field(..., min_length=1)
    answer: str = Field(..., min_length=1)
    question_type: QuestionType
    knowledge_type: KnowledgeType
    covered_node_ids: list[str] = Field(..., min_length=1)
    metadata: QuestionMetadata
    
    @field_validator('covered_node_ids')
    @classmethod
    def validate_covered_nodes(cls, v: list[str]) -> list[str]:
        """Ensure all node IDs are non-empty strings."""
        if not v:
            raise ValueError("covered_node_ids must contain at least one node")
        for node_id in v:
            if not node_id or not isinstance(node_id, str):
                raise ValueError("All node IDs must be non-empty strings")
        return v
    
    def record_hit(self) -> None:
        """Record a correct answer to this question."""
        self.metadata.hits += 1
    
    def record_miss(self) -> None:
        """Record an incorrect answer to this question."""
        self.metadata.misses += 1
    
    @property
    def success_rate(self) -> Optional[float]:
        """
        Calculate the success rate for this question.
        
        Returns:
            Success rate as a float between 0 and 1, or None if never attempted
        """
        total_attempts = self.metadata.hits + self.metadata.misses
        if total_attempts == 0:
            return None
        return self.metadata.hits / total_attempts


# ============================================================
# USER
# ============================================================


class User(BaseModel):
    """
    Represents a learner in the system.
    
    Users can join communities and have personalized mastery over nodes.
    """
    
    id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    email: str = Field(..., min_length=1)
    joined_community_ids: set[str] = Field(default_factory=set)
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Basic email validation."""
        if '@' not in v or '.' not in v.split('@')[-1]:
            raise ValueError("Invalid email format")
        return v
    
    def join_community(self, community_id: str) -> None:
        """
        Add a community to the user's joined communities.
        
        Args:
            community_id: ID of the community to join
        """
        if not community_id:
            raise ValueError("community_id cannot be empty")
        self.joined_community_ids.add(community_id)
    
    def leave_community(self, community_id: str) -> None:
        """
        Remove a community from the user's joined communities.
        
        Args:
            community_id: ID of the community to leave
            
        Raises:
            ValueError: If user is not in the community
        """
        if community_id not in self.joined_community_ids:
            raise ValueError(f"User is not a member of community '{community_id}'")
        self.joined_community_ids.remove(community_id)


# ============================================================
# COMMUNITY
# ============================================================


class Community(BaseModel):
    """
    Represents a shared learning group.
    
    Communities can define their own knowledge graphs, importance overrides,
    and question sets for collaborative learning.
    """
    
    id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    description: str = Field(default="")
    node_importance_overrides: dict[str, float] = Field(default_factory=dict)
    
    @field_validator('node_importance_overrides')
    @classmethod
    def validate_importance_overrides(cls, v: dict[str, float]) -> dict[str, float]:
        """Ensure all importance overrides are non-negative."""
        for node_id, importance in v.items():
            if importance < 0:
                raise ValueError(
                    f"Importance override for node '{node_id}' must be >= 0, got {importance}"
                )
        return v
    
    def set_node_importance(self, node_id: str, importance: float) -> None:
        """
        Set or update the importance override for a specific node.
        
        Args:
            node_id: ID of the node
            importance: New importance value (must be >= 0)
            
        Raises:
            ValueError: If importance is negative or node_id is empty
        """
        if not node_id:
            raise ValueError("node_id cannot be empty")
        if importance < 0:
            raise ValueError(f"Importance must be >= 0, got {importance}")
        self.node_importance_overrides[node_id] = importance
    
    def remove_node_importance_override(self, node_id: str) -> None:
        """
        Remove the importance override for a specific node.
        
        Args:
            node_id: ID of the node
            
        Raises:
            KeyError: If no override exists for this node
        """
        if node_id not in self.node_importance_overrides:
            raise KeyError(f"No importance override found for node '{node_id}'")
        del self.node_importance_overrides[node_id]


# ============================================================
# PHASE 3: USER KNOWLEDGE STATE & FORGETTING MODEL
# ============================================================

# Learning rate constants for review updates
SUCCESS_PKR_GAIN = 0.15
SUCCESS_STABILITY_GAIN = 1.2
FAILURE_PKR_LOSS = 0.20
FAILURE_STABILITY_LOSS = 0.8
MIN_STABILITY = 0.1
MAX_STABILITY = 10.0


class UserNodeState(BaseModel):
    """
    Represents a user's mastery of a specific knowledge node.
    
    Tracks proven knowledge rating (PKR), review history, and stability
    to model learning and forgetting over time.
    """
    
    user_id: str = Field(..., min_length=1)
    node_id: str = Field(..., min_length=1)
    proven_knowledge_rating: float = Field(default=0.0, ge=0.0, le=1.0)
    review_count: int = Field(default=0, ge=0)
    last_reviewed_at: Optional[datetime] = None
    stability: float = Field(default=1.0, gt=0)
    
    @field_validator('stability')
    @classmethod
    def validate_stability(cls, v: float) -> float:
        """Ensure stability is positive."""
        if v <= 0:
            raise ValueError(f"Stability must be > 0, got {v}")
        return v
    
    def record_success(self, timestamp: datetime) -> None:
        """
        Record a successful review (correct answer).
        
        Increases PKR and stability, updates review count and timestamp.
        
        Args:
            timestamp: When the review occurred
        """
        # Increase PKR with diminishing returns
        self.proven_knowledge_rating = min(
            1.0,
            self.proven_knowledge_rating + SUCCESS_PKR_GAIN * (1 - self.proven_knowledge_rating)
        )
        
        # Increase stability (memory consolidation)
        self.stability = min(
            MAX_STABILITY,
            self.stability * SUCCESS_STABILITY_GAIN
        )
        
        # Update metadata
        self.review_count += 1
        self.last_reviewed_at = timestamp
    
    def record_failure(self, timestamp: datetime) -> None:
        """
        Record a failed review (incorrect answer).
        
        Decreases PKR and stability, updates review count and timestamp.
        
        Args:
            timestamp: When the review occurred
        """
        # Decrease PKR proportionally
        self.proven_knowledge_rating = max(
            0.0,
            self.proven_knowledge_rating - FAILURE_PKR_LOSS * self.proven_knowledge_rating
        )
        
        # Decrease stability (memory weakening)
        self.stability = max(
            MIN_STABILITY,
            self.stability * FAILURE_STABILITY_LOSS
        )
        
        # Update metadata
        self.review_count += 1
        self.last_reviewed_at = timestamp
    
    def forgetting_score(self, now: datetime) -> float:
        """
        Calculate how much knowledge has been forgotten since last review.
        
        Uses exponential decay based on time elapsed and stability.
        
        Args:
            now: Current timestamp
            
        Returns:
            Forgetting score in [0, 1], where:
            - 0.0 = no forgetting (just reviewed)
            - 1.0 = maximum forgetting (never reviewed or very old)
        """
        # If never reviewed, maximum forgetting
        if self.last_reviewed_at is None:
            return 1.0
        
        # Calculate time elapsed in days
        elapsed = now - self.last_reviewed_at
        days_elapsed = elapsed.total_seconds() / (24 * 3600)
        
        # Exponential decay: higher stability means slower forgetting
        # Formula: 1 - e^(-days / stability)
        # This gives a value in [0, 1] that increases over time
        decay = 1.0 - math.exp(-days_elapsed / self.stability)
        
        return min(1.0, max(0.0, decay))
    
    def weakness_score(self, now: datetime, importance: float) -> float:
        """
        Calculate overall weakness score for this node.
        
        Combines low PKR, high forgetting, and importance to determine
        which topics need the most attention.
        
        Args:
            now: Current timestamp
            importance: Node importance value (>= 0)
            
        Returns:
            Weakness score (unbounded, higher = weaker)
            
        Raises:
            ValueError: If importance is negative
        """
        if importance < 0:
            raise ValueError(f"Importance must be >= 0, got {importance}")
        
        # Component 1: Low knowledge (1 - PKR)
        knowledge_weakness = 1.0 - self.proven_knowledge_rating
        
        # Component 2: Forgetting
        forgetting = self.forgetting_score(now)
        
        # Component 3: Combined weakness (knowledge gap + forgetting)
        # Average of the two components
        base_weakness = (knowledge_weakness + forgetting) / 2.0
        
        # Component 4: Importance amplification
        # Higher importance increases urgency
        importance_factor = 1.0 + (importance / 10.0)
        
        # Final weakness score
        weakness = base_weakness * importance_factor
        
        return weakness
