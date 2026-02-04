"""
Domain models for graph-based active recall system.

This package provides domain models organized into logical modules:
- enums: Enumeration types
- node: Knowledge node model
- edge: Relationship edge model
- graph: Knowledge graph with reasoning operations
- question: Question and metadata models
- user: User model
- community: Community model
- user_knowledge: User knowledge state with forgetting model
- question_bank: Question bank management
- clustering: Weak node clustering for targeted learning
- ranking: Question ranking and selection engine
"""

# Enums
from .enums import EdgeType, QuestionType, KnowledgeType

# Core models
from .node import Node
from .edge import Edge
from .graph import Graph

# Question models
from .question import Question, QuestionMetadata
from .question_bank import QuestionBank

# User models
from .user import User
from .community import Community

# Knowledge tracking
from .user_knowledge import (
    UserNodeState,
    SUCCESS_PKR_GAIN,
    SUCCESS_STABILITY_GAIN,
    FAILURE_PKR_LOSS,
    FAILURE_STABILITY_LOSS,
    MIN_STABILITY,
    MAX_STABILITY,
)

# Clustering
from .clustering import (
    Cluster,
    WeakNodeDetector,
    WeakNodeClusterer,
    MAX_CLUSTER_SIZE,
)

# Ranking
from .ranking import (
    score_cluster,
    score_question,
    compute_redundancy_penalty,
    QuestionRankingEngine,
)

__all__ = [
    # Enums
    "EdgeType",
    "QuestionType",
    "KnowledgeType",
    # Core models
    "Node",
    "Edge",
    "Graph",
    # Question models
    "Question",
    "QuestionMetadata",
    "QuestionBank",
    # User models
    "User",
    "Community",
    # Knowledge tracking
    "UserNodeState",
    "SUCCESS_PKR_GAIN",
    "SUCCESS_STABILITY_GAIN",
    "FAILURE_PKR_LOSS",
    "FAILURE_STABILITY_LOSS",
    "MIN_STABILITY",
    "MAX_STABILITY",
    # Clustering
    "Cluster",
    "WeakNodeDetector",
    "WeakNodeClusterer",
    "MAX_CLUSTER_SIZE",
    # Ranking
    "score_cluster",
    "score_question",
    "compute_redundancy_penalty",
    "QuestionRankingEngine",
]
