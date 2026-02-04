"""
Phase 9: Communities & Overrides Tests

Comprehensive unit tests for community membership, context,
community-aware ranking, and progress metrics.
"""

from datetime import datetime, timedelta
import pytest

from backend.app.domain import (
    # Community features
    CommunityMembership,
    CommunityMembershipRegistry,
    CommunityContext,
    select_next_question_for_community,
    compute_user_progress_in_community,
    compute_leaderboard,
    # Core
    Community,
    Graph,
    Node,
    Edge,
    EdgeType,
    Question,
    QuestionMetadata,
    QuestionType,
    KnowledgeType,
    QuestionBank,
    UserNodeState,
    # Clustering & Ranking
    Cluster,
    WeakNodeDetector,
    WeakNodeClusterer,
    QuestionRankingEngine,
)


# ============================================================
# TEST HELPERS
# ============================================================


def create_test_node(node_id: str, importance: float = 1.0) -> Node:
    """Helper to create a test node."""
    return Node(
        id=node_id,
        topic_name=node_id.capitalize(),
        importance=importance,
    )


def create_test_question(
    question_id: str,
    covered_nodes: list[str],
    importance: float = 1.0,
) -> Question:
    """Helper to create a test question."""
    metadata = QuestionMetadata(
        created_by="test",
        created_at=datetime.now(),
        importance=importance,
    )
    
    return Question(
        id=question_id,
        text=f"Question {question_id}",
        answer="Answer",
        question_type=QuestionType.FLASHCARD,
        knowledge_type=KnowledgeType.CONCEPT,
        covered_node_ids=covered_nodes,
        metadata=metadata,
    )


def create_test_user_state(
    node_id: str,
    user_id: str = "user1",
    pkr: float = 0.5,
    last_reviewed: datetime = None,
) -> UserNodeState:
    """Helper to create a test user state."""
    return UserNodeState(
        user_id=user_id,
        node_id=node_id,
        proven_knowledge_rating=pkr,
        stability=5.0,
        last_reviewed_at=last_reviewed or datetime.now(),
    )


# ============================================================
# COMMUNITY MEMBERSHIP TESTS
# ============================================================


class TestCommunityMembership:
    """Tests for CommunityMembership model."""
    
    def test_create_valid_membership(self):
        """Should create membership with all fields."""
        now = datetime.now()
        membership = CommunityMembership(
            community_id="comm1",
            user_id="user1",
            joined_at=now,
        )
        
        assert membership.community_id == "comm1"
        assert membership.user_id == "user1"
        assert membership.joined_at == now
    
    def test_community_id_cannot_be_empty(self):
        """Should reject empty community_id."""
        with pytest.raises(ValueError):
            CommunityMembership(
                community_id="",
                user_id="user1",
                joined_at=datetime.now(),
            )
    
    def test_user_id_cannot_be_empty(self):
        """Should reject empty user_id."""
        with pytest.raises(ValueError):
            CommunityMembership(
                community_id="comm1",
                user_id="",
                joined_at=datetime.now(),
            )


class TestCommunityMembershipRegistry:
    """Tests for CommunityMembershipRegistry."""
    
    def test_valid_membership_creation(self):
        """Should store a valid membership."""
        registry = CommunityMembershipRegistry()
        membership = CommunityMembership(
            community_id="comm1",
            user_id="user1",
            joined_at=datetime.now(),
        )
        
        registry.add_membership(membership)
        assert registry.is_member("comm1", "user1") is True
    
    def test_multiple_memberships_per_user_allowed(self):
        """Should allow same user to join multiple communities."""
        registry = CommunityMembershipRegistry()
        now = datetime.now()
        
        registry.add_membership(
            CommunityMembership(community_id="comm1", user_id="user1", joined_at=now)
        )
        registry.add_membership(
            CommunityMembership(community_id="comm2", user_id="user1", joined_at=now)
        )
        
        memberships = registry.get_memberships_for_user("user1")
        assert len(memberships) == 2
    
    def test_duplicate_membership_rejected(self):
        """Should reject duplicate (community_id, user_id) pair."""
        registry = CommunityMembershipRegistry()
        now = datetime.now()
        
        registry.add_membership(
            CommunityMembership(community_id="comm1", user_id="user1", joined_at=now)
        )
        
        with pytest.raises(ValueError, match="already exists"):
            registry.add_membership(
                CommunityMembership(community_id="comm1", user_id="user1", joined_at=now)
            )


# ============================================================
# COMMUNITY CONTEXT TESTS
# ============================================================


class TestCommunityContext:
    """Tests for CommunityContext class."""
    
    def test_get_effective_importance_with_override(self):
        """Should use community override when present."""
        # Setup
        community = Community(
            id="comm1",
            name="Test Community",
            node_importance_overrides={"node1": 10.0}
        )
        
        graph = Graph()
        bank = QuestionBank()
        
        context = CommunityContext(community, bank, graph)
        
        # Should use override
        effective = context.get_effective_importance("node1", base_importance=1.0)
        assert effective == 10.0
    
    def test_get_effective_importance_without_override(self):
        """Should use base importance when no override."""
        # Setup
        community = Community(id="comm1", name="Test")
        graph = Graph()
        bank = QuestionBank()
        
        context = CommunityContext(community, bank, graph)
        
        # Should use base
        effective = context.get_effective_importance("node1", base_importance=5.0)
        assert effective == 5.0
    
    def test_filter_questions_returns_relevant(self):
        """Should return questions covering community nodes."""
        # Setup graph
        graph = Graph()
        graph.add_node(create_test_node("python"))
        graph.add_node(create_test_node("java"))
        graph.add_node(create_test_node("cpp"))
        
        # Add edge so python and java are connected for multi-node question
        graph.add_edge(Edge(
            from_node_id="python",
            to_node_id="java",
            type=EdgeType.PREREQUISITE,
            weight=1.0,
        ))
        
        # Setup community interested in python and java
        community = Community(
            id="comm1",
            name="Python & Java",
            node_importance_overrides={
                "python": 5.0,
                "java": 5.0,
            }
        )
        
        # Setup questions
        bank = QuestionBank()
        q1 = create_test_question("q1", ["python"])
        q2 = create_test_question("q2", ["java"])
        q3 = create_test_question("q3", ["cpp"])
        q4 = create_test_question("q4", ["python", "java"])
        
        bank.add_question(q1, graph)
        bank.add_question(q2, graph)
        bank.add_question(q3, graph)
        bank.add_question(q4, graph)
        
        # Filter
        context = CommunityContext(community, bank, graph)
        relevant = context.filter_questions()
        
        # Should include q1, q2, q4 (covering python/java)
        # Should exclude q3 (only cpp)
        relevant_ids = {q.id for q in relevant}
        assert "q1" in relevant_ids
        assert "q2" in relevant_ids
        assert "q4" in relevant_ids
        assert "q3" not in relevant_ids
    
    def test_filter_questions_empty_overrides(self):
        """Should return empty list when community has no overrides."""
        community = Community(id="comm1", name="Empty")
        graph = Graph()
        graph.add_node(create_test_node("node1"))
        
        bank = QuestionBank()
        q1 = create_test_question("q1", ["node1"])
        bank.add_question(q1, graph)
        
        context = CommunityContext(community, bank, graph)
        relevant = context.filter_questions()
        
        assert len(relevant) == 0


# ============================================================
# COMMUNITY-AWARE RANKING TESTS
# ============================================================


class TestCommunityAwareRanking:
    """Tests for community-aware question selection."""
    
    def test_select_question_for_community(self):
        """Should select question using community context."""
        # Setup graph
        graph = Graph()
        graph.add_node(create_test_node("python", importance=1.0))
        graph.add_node(create_test_node("variables", importance=1.0))
        graph.add_edge(Edge(
            from_node_id="python",
            to_node_id="variables",
            type=EdgeType.PREREQUISITE,
            weight=1.0,
        ))
        
        # Setup community with overrides
        community = Community(
            id="comm1",
            name="Python Community",
            node_importance_overrides={
                "python": 10.0,  # High community importance
                "variables": 8.0,
            }
        )
        
        # Setup questions
        bank = QuestionBank()
        q1 = create_test_question("q1", ["python"], importance=1.0)
        q2 = create_test_question("q2", ["variables"], importance=1.0)
        bank.add_question(q1, graph)
        bank.add_question(q2, graph)
        
        # Setup weak states
        now = datetime.now()
        old = now - timedelta(days=30)
        user_states = {
            "python": create_test_user_state("python", pkr=0.2, last_reviewed=old),
            "variables": create_test_user_state("variables", pkr=0.2, last_reviewed=old),
        }
        
        # Create clusters
        importance_lookup = {node.id: node.importance for node in graph.nodes.values()}
        weak_nodes = WeakNodeDetector.get_weak_nodes(
            user_node_states=list(user_states.values()),
            now=now,
            importance_lookup=importance_lookup,
            weakness_threshold=0.5,
        )
        
        clusterer = WeakNodeClusterer(graph=graph, max_hops=2, allowed_edge_types=None)
        clusters = clusterer.generate_clusters(weak_nodes)
        
        # Create ranking engine
        engine = QuestionRankingEngine
        
        # Select question with community context
        question = select_next_question_for_community(
            community=community,
            ranking_engine=engine,
            clusters=clusters,
            question_bank=bank,
            user_node_states=user_states,
            recently_attempted_question_ids=set(),
            now=now,
        )
        
        # Should return a question
        assert question is not None
        assert question.id in ["q1", "q2"]

    def test_ranking_respects_importance_overrides(self):
        """Should favor questions tied to higher community importance."""
        graph = Graph()
        graph.add_node(create_test_node("high", importance=1.0))
        graph.add_node(create_test_node("low", importance=1.0))
        graph.add_edge(Edge(
            from_node_id="high",
            to_node_id="low",
            type=EdgeType.PREREQUISITE,
            weight=1.0,
        ))
        
        community = Community(
            id="comm1",
            name="Importance Test",
            node_importance_overrides={
                "high": 10.0,
                "low": 1.0,
            }
        )
        
        bank = QuestionBank()
        q_high = create_test_question("q_high", ["high"], importance=1.0)
        q_low = create_test_question("q_low", ["low"], importance=1.0)
        bank.add_question(q_high, graph)
        bank.add_question(q_low, graph)
        
        now = datetime.now()
        old = now - timedelta(days=30)
        user_states = {
            "high": create_test_user_state("high", pkr=0.2, last_reviewed=old),
            "low": create_test_user_state("low", pkr=0.2, last_reviewed=old),
        }
        
        importance_lookup = {node.id: node.importance for node in graph.nodes.values()}
        weak_nodes = WeakNodeDetector.get_weak_nodes(
            user_node_states=list(user_states.values()),
            now=now,
            importance_lookup=importance_lookup,
            weakness_threshold=0.5,
        )
        
        clusterer = WeakNodeClusterer(graph=graph, max_hops=2, allowed_edge_types=None)
        clusters = clusterer.generate_clusters(weak_nodes)
        
        engine = QuestionRankingEngine
        question = select_next_question_for_community(
            community=community,
            ranking_engine=engine,
            clusters=clusters,
            question_bank=bank,
            user_node_states=user_states,
            recently_attempted_question_ids=set(),
            now=now,
        )
        
        assert question is not None
        assert question.id == "q_high"

    def test_ranking_is_deterministic(self):
        """Should return the same question for identical inputs."""
        graph = Graph()
        graph.add_node(create_test_node("node1", importance=1.0))
        graph.add_node(create_test_node("node2", importance=1.0))
        graph.add_edge(Edge(
            from_node_id="node1",
            to_node_id="node2",
            type=EdgeType.PREREQUISITE,
            weight=1.0,
        ))
        
        community = Community(
            id="comm1",
            name="Determinism",
            node_importance_overrides={"node1": 5.0, "node2": 5.0}
        )
        
        bank = QuestionBank()
        q1 = create_test_question("q1", ["node1"], importance=1.0)
        q2 = create_test_question("q2", ["node2"], importance=1.0)
        bank.add_question(q1, graph)
        bank.add_question(q2, graph)
        
        now = datetime.now()
        old = now - timedelta(days=30)
        user_states = {
            "node1": create_test_user_state("node1", pkr=0.2, last_reviewed=old),
            "node2": create_test_user_state("node2", pkr=0.2, last_reviewed=old),
        }
        
        importance_lookup = {node.id: node.importance for node in graph.nodes.values()}
        weak_nodes = WeakNodeDetector.get_weak_nodes(
            user_node_states=list(user_states.values()),
            now=now,
            importance_lookup=importance_lookup,
            weakness_threshold=0.5,
        )
        
        clusterer = WeakNodeClusterer(graph=graph, max_hops=2, allowed_edge_types=None)
        clusters = clusterer.generate_clusters(weak_nodes)
        
        engine = QuestionRankingEngine
        q_first = select_next_question_for_community(
            community=community,
            ranking_engine=engine,
            clusters=clusters,
            question_bank=bank,
            user_node_states=user_states,
            recently_attempted_question_ids=set(),
            now=now,
        )
        q_second = select_next_question_for_community(
            community=community,
            ranking_engine=engine,
            clusters=clusters,
            question_bank=bank,
            user_node_states=user_states,
            recently_attempted_question_ids=set(),
            now=now,
        )
        
        assert q_first is not None
        assert q_second is not None
        assert q_first.id == q_second.id
    
    def test_select_returns_none_when_no_relevant_questions(self):
        """Should return None when no community-relevant questions."""
        # Setup
        graph = Graph()
        graph.add_node(create_test_node("node1"))
        
        # Community interested in different node
        community = Community(
            id="comm1",
            name="Test",
            node_importance_overrides={"other_node": 5.0}
        )
        
        # Question doesn't cover community nodes
        bank = QuestionBank()
        q1 = create_test_question("q1", ["node1"])
        bank.add_question(q1, graph)
        
        now = datetime.now()
        user_states = {
            "node1": create_test_user_state("node1", pkr=0.2, last_reviewed=now - timedelta(days=30))
        }
        
        importance_lookup = {node.id: node.importance for node in graph.nodes.values()}
        weak_nodes = WeakNodeDetector.get_weak_nodes(
            user_node_states=list(user_states.values()),
            now=now,
            importance_lookup=importance_lookup,
            weakness_threshold=0.5,
        )
        
        clusterer = WeakNodeClusterer(graph=graph, max_hops=2, allowed_edge_types=None)
        clusters = clusterer.generate_clusters(weak_nodes)
        
        engine = QuestionRankingEngine
        
        question = select_next_question_for_community(
            community=community,
            ranking_engine=engine,
            clusters=clusters,
            question_bank=bank,
            user_node_states=user_states,
            recently_attempted_question_ids=set(),
            now=now,
        )
        
        # No relevant questions
        assert question is None


# ============================================================
# PROGRESS METRICS TESTS
# ============================================================


class TestUserProgress:
    """Tests for user progress computation."""
    
    def test_compute_progress_with_studied_nodes(self):
        """Should compute average PKR of community nodes."""
        # Setup community
        community = Community(
            id="comm1",
            name="Python",
            node_importance_overrides={
                "python": 5.0,
                "variables": 5.0,
                "functions": 5.0,
            }
        )
        
        # User has studied all nodes
        user_states = {
            "python": create_test_user_state("python", pkr=0.8),
            "variables": create_test_user_state("variables", pkr=0.6),
            "functions": create_test_user_state("functions", pkr=0.7),
        }
        
        progress = compute_user_progress_in_community(user_states, community)
        
        # Average: (0.8 + 0.6 + 0.7) / 3 = 0.7
        assert progress == pytest.approx(0.7, abs=0.001)
    
    def test_compute_progress_with_unstudied_nodes(self):
        """Should treat unstudied nodes as 0.0 PKR."""
        community = Community(
            id="comm1",
            name="Test",
            node_importance_overrides={
                "node1": 5.0,
                "node2": 5.0,
            }
        )
        
        # User only studied node1
        user_states = {
            "node1": create_test_user_state("node1", pkr=0.8),
        }
        
        progress = compute_user_progress_in_community(user_states, community)
        
        # Average: (0.8 + 0.0) / 2 = 0.4
        assert progress == pytest.approx(0.4, abs=0.001)
    
    def test_compute_progress_empty_community(self):
        """Should return 0.0 for community with no overrides."""
        community = Community(id="comm1", name="Empty")
        user_states = {
            "node1": create_test_user_state("node1", pkr=0.8),
        }
        
        progress = compute_user_progress_in_community(user_states, community)
        
        assert progress == 0.0
    
    def test_compute_progress_no_user_states(self):
        """Should return 0.0 when user has no states."""
        community = Community(
            id="comm1",
            name="Test",
            node_importance_overrides={"node1": 5.0}
        )
        
        progress = compute_user_progress_in_community({}, community)
        
        assert progress == 0.0


class TestLeaderboard:
    """Tests for leaderboard computation."""
    
    def test_compute_leaderboard_sorts_descending(self):
        """Should sort users by progress descending."""
        community = Community(
            id="comm1",
            name="Python",
            node_importance_overrides={
                "python": 5.0,
                "variables": 5.0,
            }
        )
        
        # Three users with different progress
        users_states = {
            "user1": {
                "python": create_test_user_state("python", user_id="user1", pkr=0.9),
                "variables": create_test_user_state("variables", user_id="user1", pkr=0.8),
            },
            "user2": {
                "python": create_test_user_state("python", user_id="user2", pkr=0.5),
                "variables": create_test_user_state("variables", user_id="user2", pkr=0.6),
            },
            "user3": {
                "python": create_test_user_state("python", user_id="user3", pkr=0.7),
                "variables": create_test_user_state("variables", user_id="user3", pkr=0.7),
            },
        }
        
        leaderboard = compute_leaderboard(users_states, community)
        
        # Should be sorted: user1 (0.85), user3 (0.7), user2 (0.55)
        assert len(leaderboard) == 3
        assert leaderboard[0][0] == "user1"
        assert leaderboard[0][1] == pytest.approx(0.85, abs=0.001)
        assert leaderboard[1][0] == "user3"
        assert leaderboard[1][1] == pytest.approx(0.7, abs=0.001)
        assert leaderboard[2][0] == "user2"
        assert leaderboard[2][1] == pytest.approx(0.55, abs=0.001)
    
    def test_leaderboard_with_tied_scores(self):
        """Should use user_id for deterministic tie-breaking."""
        community = Community(
            id="comm1",
            name="Test",
            node_importance_overrides={"node1": 5.0}
        )
        
        # Two users with same score
        users_states = {
            "userB": {
                "node1": create_test_user_state("node1", user_id="userB", pkr=0.5),
            },
            "userA": {
                "node1": create_test_user_state("node1", user_id="userA", pkr=0.5),
            },
        }
        
        leaderboard = compute_leaderboard(users_states, community)
        
        # Both have 0.5, should be sorted by user_id
        assert leaderboard[0][0] == "userA"
        assert leaderboard[1][0] == "userB"
    
    def test_leaderboard_empty_users(self):
        """Should return empty list for no users."""
        community = Community(
            id="comm1",
            name="Test",
            node_importance_overrides={"node1": 5.0}
        )
        
        leaderboard = compute_leaderboard({}, community)
        
        assert leaderboard == []


# ============================================================
# INTEGRATION TESTS
# ============================================================


class TestCommunityIntegration:
    """Integration tests for community features."""
    
    def test_full_community_workflow(self):
        """Should handle complete community workflow."""
        # 1. Create graph
        graph = Graph()
        for node_id in ["python", "variables", "functions", "loops"]:
            graph.add_node(create_test_node(node_id, importance=1.0))
        
        graph.add_edge(Edge(
            from_node_id="python",
            to_node_id="variables",
            type=EdgeType.PREREQUISITE,
            weight=1.0,
        ))
        graph.add_edge(Edge(
            from_node_id="variables",
            to_node_id="functions",
            type=EdgeType.PREREQUISITE,
            weight=1.0,
        ))
        
        # 2. Create Python-focused community
        community = Community(
            id="python_community",
            name="Python Learners",
            description="Focus on Python fundamentals",
            node_importance_overrides={
                "python": 10.0,
                "variables": 8.0,
                "functions": 7.0,
            }
        )
        
        # 3. Setup questions
        bank = QuestionBank()
        q1 = create_test_question("q1", ["python"])
        q2 = create_test_question("q2", ["variables"])
        q3 = create_test_question("q3", ["functions"])
        q4 = create_test_question("q4", ["loops"])  # Not in community
        
        bank.add_question(q1, graph)
        bank.add_question(q2, graph)
        bank.add_question(q3, graph)
        bank.add_question(q4, graph)
        
        # 4. Create community context
        context = CommunityContext(community, bank, graph)
        
        # Verify filtering
        relevant = context.filter_questions()
        relevant_ids = {q.id for q in relevant}
        assert "q1" in relevant_ids
        assert "q2" in relevant_ids
        assert "q3" in relevant_ids
        assert "q4" not in relevant_ids
        
        # 5. Setup user states
        now = datetime.now()
        old = now - timedelta(days=30)
        
        user1_states = {
            "python": create_test_user_state("python", "user1", pkr=0.8, last_reviewed=old),
            "variables": create_test_user_state("variables", "user1", pkr=0.6, last_reviewed=old),
            "functions": create_test_user_state("functions", "user1", pkr=0.2, last_reviewed=old),
        }
        
        user2_states = {
            "python": create_test_user_state("python", "user2", pkr=0.5, last_reviewed=old),
            "variables": create_test_user_state("variables", "user2", pkr=0.5, last_reviewed=old),
            "functions": create_test_user_state("functions", "user2", pkr=0.1, last_reviewed=old),
        }
        
        # 6. Compute progress
        user1_progress = compute_user_progress_in_community(user1_states, community)
        user2_progress = compute_user_progress_in_community(user2_states, community)
        
        assert user1_progress > user2_progress
        
        # 7. Compute leaderboard
        leaderboard = compute_leaderboard(
            {"user1": user1_states, "user2": user2_states},
            community,
        )
        
        assert leaderboard[0][0] == "user1"
        assert leaderboard[1][0] == "user2"
        
        # 8. Select question for user2 (weaker user)
        importance_lookup = {node.id: node.importance for node in graph.nodes.values()}
        weak_nodes = WeakNodeDetector.get_weak_nodes(
            user_node_states=list(user2_states.values()),
            now=now,
            importance_lookup=importance_lookup,
            weakness_threshold=0.5,
        )
        
        clusterer = WeakNodeClusterer(graph=graph, max_hops=2, allowed_edge_types=None)
        clusters = clusterer.generate_clusters(weak_nodes)
        
        engine = QuestionRankingEngine
        
        question = select_next_question_for_community(
            community=community,
            ranking_engine=engine,
            clusters=clusters,
            question_bank=bank,
            user_node_states=user2_states,
            recently_attempted_question_ids=set(),
            now=now,
        )
        
        # Should get a community-relevant question
        assert question is not None
        assert question.id in ["q1", "q2", "q3"]
        
        # 9. Create memberships
        registry = CommunityMembershipRegistry()
        registry.add_membership(
            CommunityMembership(community_id=community.id, user_id="user1", joined_at=now)
        )
        registry.add_membership(
            CommunityMembership(community_id=community.id, user_id="user2", joined_at=now)
        )
        
        assert registry.is_member(community.id, "user1") is True
        assert registry.is_member(community.id, "user2") is True

    def test_multiple_users_same_community(self):
        """Should handle multiple users in the same community."""
        community = Community(
            id="comm1",
            name="Shared",
            node_importance_overrides={"node1": 5.0}
        )
        
        user1_states = {"node1": create_test_user_state("node1", "user1", pkr=0.9)}
        user2_states = {"node1": create_test_user_state("node1", "user2", pkr=0.4)}
        
        leaderboard = compute_leaderboard(
            {"user1": user1_states, "user2": user2_states},
            community,
        )
        
        assert leaderboard[0][0] == "user1"
        assert leaderboard[1][0] == "user2"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
