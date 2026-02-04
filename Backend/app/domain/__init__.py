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
- session: Revision session orchestration
- material: Material models for content ingestion
- ingestion: Content ingestion APIs
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

# Session
from .session import (
    SessionConfig,
    RevisionSession,
)

# Material and Ingestion (Phase 8)
from .material import (
    Material,
    MaterialType,
    MaterialRegistry,
)

from .ingestion import (
    create_node_from_material,
    create_question_from_material,
    CSVQuestionImporter,
)

# Community Features (Phase 9)
from .community_features import (
    CommunityMembership,
    CommunityMembershipRegistry,
    CommunityContext,
    select_next_question_for_community,
    compute_user_progress_in_community,
    compute_leaderboard,
)

# Interjection and Revision Planning (Phase 10)
from .interjection import (
    ContentSession,
    InterjectionPolicy,
    InterjectionEngine,
    RevisionPlanner,
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
    # Session
    "SessionConfig",
    "RevisionSession",
    # Material and Ingestion
    "Material",
    "MaterialType",
    "MaterialRegistry",
    "create_node_from_material",
    "create_question_from_material",
    "CSVQuestionImporter",
    # Community Features
    "CommunityMembership",
    "CommunityMembershipRegistry",
    "CommunityContext",
    "select_next_question_for_community",
    "compute_user_progress_in_community",
    "compute_leaderboard",
    # Interjection and Revision Planning
    "ContentSession",
    "InterjectionPolicy",
    "InterjectionEngine",
    "RevisionPlanner",
]
