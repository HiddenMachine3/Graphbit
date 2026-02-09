"""Community features: membership, context, and metrics."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from .community import Community
from .question_bank import QuestionBank
from .question import Question
from .graph import Graph
from .user_knowledge import UserNodeState
from .clustering import Cluster
from .ranking import QuestionRankingEngine


# ============================================================
# COMMUNITY MEMBERSHIP
# ============================================================


class CommunityMembership(BaseModel):
    """
    Represents a user's membership in a community.
    
    Tracks when users join learning communities for shared context.
    """
    
    community_id: str = Field(..., min_length=1)
    user_id: str = Field(..., min_length=1)
    joined_at: datetime


class CommunityMembershipRegistry:
    """
    Registry for community memberships.
    
    Allows multiple memberships per user across communities,
    but rejects duplicate (community_id, user_id) pairs.
    """
    
    def __init__(self) -> None:
        self._memberships: dict[tuple[str, str], CommunityMembership] = {}
    
    def add_membership(self, membership: CommunityMembership) -> None:
        """Add a membership, rejecting duplicates."""
        key = (membership.community_id, membership.user_id)
        if key in self._memberships:
            raise ValueError(
                f"Membership already exists for user '{membership.user_id}' "
                f"in community '{membership.community_id}'"
            )
        self._memberships[key] = membership
    
    def is_member(self, community_id: str, user_id: str) -> bool:
        """Check if a user is a member of a community."""
        return (community_id, user_id) in self._memberships
    
    def get_memberships_for_user(self, user_id: str) -> list[CommunityMembership]:
        """Get all memberships for a user."""
        return [m for (c_id, u_id), m in self._memberships.items() if u_id == user_id]


# ============================================================
# COMMUNITY CONTEXT
# ============================================================


class CommunityContext:
    """
    Provides community-scoped views of data.
    
    Applies community importance overrides and filters content
    to community-relevant scope.
    """
    
    def __init__(
        self,
        community: Community,
        question_bank: QuestionBank,
        graph: Graph,
    ):
        """
        Initialize community context.
        
        Args:
            community: The community
            question_bank: Question bank for filtering
            graph: Knowledge graph for node lookups
        """
        self.community = community
        self.question_bank = question_bank
        self.graph = graph
    
    def get_effective_importance(
        self,
        project_id: str,
        node_id: str,
        base_importance: float,
    ) -> float:
        """
        Get effective importance for a node in this community within a project.
        
        Uses community override if present, otherwise falls back
        to base importance.
        
        Args:
            project_id: ID of the project
            node_id: ID of the node
            base_importance: Default importance value
            
        Returns:
            Effective importance for this community in this project
        """
        project_overrides = self.community.node_importance_overrides.get(project_id, {})
        if node_id in project_overrides:
            return project_overrides[node_id]
        return base_importance
    
    def filter_questions(self, project_id: str) -> list[Question]:
        """
        Return only questions relevant to this community in a specific project.
        
        A question is relevant if:
        1. It belongs to the specified project
        2. At least one of its covered nodes has a community importance override
        
        Args:
            project_id: ID of the project to filter by
        
        Returns:
            List of community-relevant questions in the project
        """
        relevant_questions = []
        project_overrides = self.community.node_importance_overrides.get(project_id, {})
        
        for question in self.question_bank.questions.values():
            # Check if question belongs to this project
            if question.project_id != project_id:
                continue
            
            # Check if any covered node has community override
            for node_id in question.covered_node_ids:
                if node_id in project_overrides:
                    relevant_questions.append(question)
                    break  # Only add once per question
        
        return relevant_questions


# ============================================================
# COMMUNITY-AWARE RANKING
# ============================================================


def select_next_question_for_community(
    community: Community,
    project_id: str,
    ranking_engine: QuestionRankingEngine,
    clusters: list[Cluster],
    question_bank: QuestionBank,
    user_node_states: dict[str, UserNodeState],
    recently_attempted_question_ids: set[str],
    now: datetime,
) -> Optional[Question]:
    """
    Select next question for a user in a community context within a project.
    
    Applies community importance overrides and filters questions
    to community scope within the project, then delegates ranking to Phase 6 engine.
    
    Args:
        community: The community providing context
        project_id: The project context
        ranking_engine: Phase 6 ranking engine
        clusters: Weak node clusters
        question_bank: Available questions
        user_node_states: User's knowledge state
        recently_attempted_question_ids: Recently attempted questions
        now: Current timestamp
        
    Returns:
        Selected question, or None if no suitable question found
    """
    # Build importance lookup with community overrides for this project
    importance_lookup: dict[str, float] = {}
    graph = getattr(ranking_engine, "graph", None)
    if graph is not None:
        for node_id, node in graph.nodes.items():
            importance_lookup[node_id] = node.importance
    else:
        for node_id in user_node_states.keys():
            importance_lookup[node_id] = 1.0
    
    # Apply community overrides for this project
    project_overrides = community.node_importance_overrides.get(project_id, {})
    for node_id, override in project_overrides.items():
        importance_lookup[node_id] = override
    
    # Filter questions to community scope within project
    if not project_overrides:
        return None
    
    relevant_questions = [
        q for q in question_bank.questions.values()
        if q.project_id == project_id and any(node_id in project_overrides for node_id in q.covered_node_ids)
    ]
    
    # If no relevant questions, return None
    if not relevant_questions:
        return None
    
    # Create temporary question bank with only relevant questions
    temp_bank = QuestionBank()
    for q in relevant_questions:
        # Add without validation since they're already validated
        temp_bank.questions[q.id] = q
    
    # Delegate to Phase 6 ranking (static method)
    return ranking_engine.select_next_question(
        clusters=clusters,
        question_bank=temp_bank,
        user_node_states=user_node_states,
        importance_lookup=importance_lookup,
        recently_attempted_question_ids=recently_attempted_question_ids,
        now=now,
    )


# ============================================================
# COMMUNITY PROGRESS METRICS
# ============================================================


def compute_user_progress_in_community(
    user_node_states: dict[str, UserNodeState],
    community: Community,
    project_id: str,
) -> float:
    """
    Compute user's learning progress in community context within a project.
    
    Progress is the average PKR of all nodes with community
    importance overrides (community-relevant nodes) in the project.
    
    Args:
        user_node_states: User's knowledge states
        community: Community defining scope
        project_id: Project context
        
    Returns:
        Average PKR (0.0 to 1.0), or 0.0 if no relevant nodes
    """
    project_overrides = community.node_importance_overrides.get(project_id, {})
    relevant_node_ids = set(project_overrides.keys())
    
    if not relevant_node_ids:
        return 0.0
    
    # Collect PKR values for relevant nodes
    pkr_values = []
    for node_id in relevant_node_ids:
        if node_id in user_node_states:
            pkr_values.append(user_node_states[node_id].proven_knowledge_rating)
        else:
            # Node not yet studied, assume 0.0
            pkr_values.append(0.0)
    
    if not pkr_values:
        return 0.0
    
    return sum(pkr_values) / len(pkr_values)


def compute_leaderboard(
    users_node_states: dict[str, dict[str, UserNodeState]],
    community: Community,
    project_id: str,
) -> list[tuple[str, float]]:
    """
    Compute community leaderboard for a specific project.
    
    Ranks users by their progress in community-relevant content within the project.
    
    Args:
        users_node_states: Mapping of user_id to their node states
        community: Community defining scope
        project_id: Project context
        
    Returns:
        List of (user_id, score) tuples, sorted descending by score.
        Score is average PKR of community-relevant nodes in the project.
    """
    leaderboard: list[tuple[str, float]] = []
    
    for user_id, node_states in users_node_states.items():
        score = compute_user_progress_in_community(node_states, community, project_id)
        leaderboard.append((user_id, score))
    
    # Sort descending by score, then by user_id for determinism
    leaderboard.sort(key=lambda x: (-x[1], x[0]))
    
    return leaderboard
