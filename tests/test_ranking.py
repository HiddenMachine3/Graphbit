"""
Phase 6: Question Ranking & Selection Engine Tests

Comprehensive unit tests for cluster scoring, question scoring,
and heap-based question selection.
"""

from datetime import datetime, timedelta
import pytest

from backend.app.domain import (
    # Ranking
    score_cluster,
    score_question,
    compute_redundancy_penalty,
    QuestionRankingEngine,
    # Clustering
    Cluster,
    # Questions
    Question,
    QuestionMetadata,
    QuestionType,
    KnowledgeType,
    QuestionBank,
    # Graph
    Graph,
    Node,
    Edge,
    EdgeType,
    # User knowledge
    UserNodeState,
)


# ============================================================
# TEST HELPERS
# ============================================================


def create_node(node_id: str) -> Node:
    """Helper to create Node."""
    return Node(id=node_id, topic_name=node_id.capitalize())


def create_edge(from_id: str, to_id: str) -> Edge:
    """Helper to create Edge."""
    return Edge(
        from_node_id=from_id,
        to_node_id=to_id,
        type=EdgeType.PREREQUISITE,
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


def create_question(
    question_id: str,
    covered_nodes: list[str],
    importance: float = 1.0,
    difficulty: int = 3
) -> Question:
    """Helper to create Question."""
    metadata = QuestionMetadata(
        created_by="test",
        created_at=datetime.now(),
        importance=importance
    )
    
    return Question(
        id=question_id,
        text=f"Question {question_id}",
        answer="Answer",
        question_type=QuestionType.FLASHCARD,
        knowledge_type=KnowledgeType.CONCEPT,
        covered_node_ids=covered_nodes,
        metadata=metadata,
        difficulty=difficulty
    )


# ============================================================
# CLUSTER SCORING TESTS
# ============================================================


class TestClusterScoring:
    """Tests for cluster scoring function."""
    
    def test_score_empty_cluster(self):
        """Should return 0 for empty cluster."""
        cluster = Cluster(node_ids={"a", "b"}, seed_node_id="a")
        # Remove nodes to make it empty (violates validation but testing edge case)
        cluster.node_ids = set()
        
        score = score_cluster(cluster, {}, datetime.now(), {})
        assert score == 0.0
    
    def test_score_cluster_with_weak_nodes(self):
        """Should score high for weak nodes."""
        now = datetime.now()
        old_review = now - timedelta(days=30)
        
        cluster = Cluster(node_ids={"node1", "node2"}, seed_node_id="node1")
        
        user_states = {
            "node1": create_user_state("node1", pkr=0.1, last_reviewed=old_review),
            "node2": create_user_state("node2", pkr=0.2, last_reviewed=old_review),
        }
        
        importance = {"node1": 1.0, "node2": 1.0}
        
        score = score_cluster(cluster, user_states, now, importance)
        
        # Should be high score (weak nodes, old reviews)
        assert score > 0.5
    
    def test_score_cluster_with_strong_nodes(self):
        """Should score low for strong nodes."""
        now = datetime.now()
        
        cluster = Cluster(node_ids={"node1", "node2"}, seed_node_id="node1")
        
        user_states = {
            "node1": create_user_state("node1", pkr=0.9, last_reviewed=now),
            "node2": create_user_state("node2", pkr=0.95, last_reviewed=now),
        }
        
        importance = {"node1": 1.0, "node2": 1.0}
        
        score = score_cluster(cluster, user_states, now, importance)
        
        # Should be low score (strong nodes, recent reviews)
        assert score < 0.5
    
    def test_score_cluster_with_missing_user_state(self):
        """Should treat missing state as maximum weakness."""
        now = datetime.now()
        
        cluster = Cluster(node_ids={"never_reviewed", "reviewed"}, seed_node_id="never_reviewed")
        
        user_states = {
            "reviewed": create_user_state("reviewed", pkr=0.9, last_reviewed=now),
            # "never_reviewed" has no state
        }
        
        importance = {"never_reviewed": 1.0, "reviewed": 1.0}
        
        score = score_cluster(cluster, user_states, now, importance)
        
        # Should be high due to never_reviewed node
        assert score > 0.5
    
    def test_score_cluster_deterministic(self):
        """Should return same score for same inputs."""
        now = datetime.now()
        old_review = now - timedelta(days=30)
        
        cluster = Cluster(node_ids={"a", "b"}, seed_node_id="a")
        
        user_states = {
            "a": create_user_state("a", pkr=0.3, last_reviewed=old_review),
            "b": create_user_state("b", pkr=0.4, last_reviewed=old_review),
        }
        
        importance = {"a": 1.0, "b": 1.0}
        
        score1 = score_cluster(cluster, user_states, now, importance)
        score2 = score_cluster(cluster, user_states, now, importance)
        
        assert score1 == score2


# ============================================================
# REDUNDANCY PENALTY TESTS
# ============================================================


class TestRedundancyPenalty:
    """Tests for redundancy penalty computation."""
    
    def test_penalty_for_recently_attempted(self):
        """Should apply penalty to recently attempted questions."""
        question = create_question("q1", ["node1"])
        recently_attempted = {"q1", "q2"}
        
        penalty = compute_redundancy_penalty(question, recently_attempted)
        
        assert penalty > 0
    
    def test_no_penalty_for_fresh_questions(self):
        """Should not penalize fresh questions."""
        question = create_question("q1", ["node1"])
        recently_attempted = {"q2", "q3"}
        
        penalty = compute_redundancy_penalty(question, recently_attempted)
        
        assert penalty == 0.0
    
    def test_penalty_with_empty_recent_set(self):
        """Should not penalize when no recent attempts."""
        question = create_question("q1", ["node1"])
        recently_attempted = set()
        
        penalty = compute_redundancy_penalty(question, recently_attempted)
        
        assert penalty == 0.0
    
    def test_penalty_deterministic(self):
        """Should return same penalty for same inputs."""
        question = create_question("q1", ["node1"])
        recently_attempted = {"q1"}
        
        penalty1 = compute_redundancy_penalty(question, recently_attempted)
        penalty2 = compute_redundancy_penalty(question, recently_attempted)
        
        assert penalty1 == penalty2


# ============================================================
# QUESTION SCORING TESTS
# ============================================================


class TestQuestionScoring:
    """Tests for question scoring function."""
    
    def test_score_increases_with_cluster_score(self):
        """Should score higher for higher cluster scores."""
        question = create_question("q1", ["node1"], importance=1.0)
        
        score_low = score_question(question, cluster_score=0.5, redundancy_penalty=0.0)
        score_high = score_question(question, cluster_score=1.0, redundancy_penalty=0.0)
        
        assert score_high > score_low
    
    def test_score_increases_with_question_importance(self):
        """Should score higher for more important questions."""
        q_low = create_question("q1", ["node1"], importance=1.0)
        q_high = create_question("q2", ["node1"], importance=5.0)
        
        score_low = score_question(q_low, cluster_score=1.0, redundancy_penalty=0.0)
        score_high = score_question(q_high, cluster_score=1.0, redundancy_penalty=0.0)
        
        assert score_high > score_low
    
    def test_score_decreases_with_redundancy_penalty(self):
        """Should score lower with higher redundancy penalty."""
        question = create_question("q1", ["node1"])
        
        score_no_penalty = score_question(question, cluster_score=1.0, redundancy_penalty=0.0)
        score_with_penalty = score_question(question, cluster_score=1.0, redundancy_penalty=0.5)
        
        assert score_with_penalty < score_no_penalty
    
    def test_score_non_negative(self):
        """Should never return negative scores."""
        question = create_question("q1", ["node1"])
        
        # High penalty, low cluster score
        score = score_question(question, cluster_score=0.1, redundancy_penalty=1.0)
        
        assert score >= 0.0
    
    def test_score_deterministic(self):
        """Should return same score for same inputs."""
        question = create_question("q1", ["node1"], importance=2.0)
        
        score1 = score_question(question, cluster_score=0.8, redundancy_penalty=0.2)
        score2 = score_question(question, cluster_score=0.8, redundancy_penalty=0.2)
        
        assert score1 == score2


# ============================================================
# RANKING ENGINE TESTS
# ============================================================


class TestQuestionRankingEngine:
    """Tests for QuestionRankingEngine."""
    
    def test_select_question_from_single_cluster(self):
        """Should select question from single cluster."""
        # Setup graph
        graph = Graph()
        graph.add_node(create_node("python"))
        graph.add_node(create_node("variables"))
        graph.add_edge(create_edge("python", "variables"))
        
        # Setup cluster
        cluster = Cluster(node_ids={"python", "variables"}, seed_node_id="python")
        
        # Setup question bank
        bank = QuestionBank()
        q1 = create_question("q1", ["python"])
        bank.add_question(q1, graph)
        
        # Setup user states (weak)
        now = datetime.now()
        old_review = now - timedelta(days=30)
        user_states = {
            "python": create_user_state("python", pkr=0.2, last_reviewed=old_review),
        }
        
        # Select question
        selected = QuestionRankingEngine.select_next_question(
            clusters=[cluster],
            question_bank=bank,
            user_node_states=user_states,
            importance_lookup={"python": 1.0, "variables": 1.0},
            recently_attempted_question_ids=set(),
            now=now
        )
        
        assert selected is not None
        assert selected.id == "q1"
    
    def test_select_highest_scoring_question(self):
        """Should select question with highest score."""
        # Setup graph
        graph = Graph()
        graph.add_node(create_node("a"))
        graph.add_node(create_node("b"))
        graph.add_edge(create_edge("a", "b"))
        
        # Setup cluster
        cluster = Cluster(node_ids={"a", "b"}, seed_node_id="a")
        
        # Setup questions with different importance
        bank = QuestionBank()
        q_low = create_question("q_low", ["a"], importance=1.0)
        q_high = create_question("q_high", ["a"], importance=10.0)
        bank.add_question(q_low, graph)
        bank.add_question(q_high, graph)
        
        # Setup user states
        now = datetime.now()
        old_review = now - timedelta(days=30)
        user_states = {
            "a": create_user_state("a", pkr=0.1, last_reviewed=old_review),
        }
        
        # Select question
        selected = QuestionRankingEngine.select_next_question(
            clusters=[cluster],
            question_bank=bank,
            user_node_states=user_states,
            importance_lookup={"a": 1.0, "b": 1.0},
            recently_attempted_question_ids=set(),
            now=now
        )
        
        # Should select high-importance question
        assert selected.id == "q_high"
    
    def test_avoids_recently_attempted_questions(self):
        """Should prefer fresh questions over recently attempted ones."""
        # Setup graph
        graph = Graph()
        graph.add_node(create_node("node"))
        
        # Setup cluster
        cluster = Cluster(node_ids={"node", "node2"}, seed_node_id="node")
        graph.add_node(create_node("node2"))
        graph.add_edge(create_edge("node", "node2"))
        
        # Setup questions
        bank = QuestionBank()
        q_recent = create_question("q_recent", ["node"], importance=5.0)
        q_fresh = create_question("q_fresh", ["node"], importance=5.0)
        bank.add_question(q_recent, graph)
        bank.add_question(q_fresh, graph)
        
        # Setup user states
        now = datetime.now()
        old_review = now - timedelta(days=30)
        user_states = {
            "node": create_user_state("node", pkr=0.2, last_reviewed=old_review),
        }
        
        # Select with recently attempted
        selected = QuestionRankingEngine.select_next_question(
            clusters=[cluster],
            question_bank=bank,
            user_node_states=user_states,
            importance_lookup={"node": 1.0, "node2": 1.0},
            recently_attempted_question_ids={"q_recent"},
            now=now
        )
        
        # Should prefer fresh question
        assert selected.id == "q_fresh"
    
    def test_returns_none_for_empty_clusters(self):
        """Should return None when no clusters provided."""
        bank = QuestionBank()
        
        selected = QuestionRankingEngine.select_next_question(
            clusters=[],
            question_bank=bank,
            user_node_states={},
            importance_lookup={},
            recently_attempted_question_ids=set(),
            now=datetime.now()
        )
        
        assert selected is None
    
    def test_returns_none_when_no_questions_found(self):
        """Should return None when no questions cover clusters."""
        cluster = Cluster(node_ids={"a", "b"}, seed_node_id="a")
        bank = QuestionBank()  # Empty bank
        
        selected = QuestionRankingEngine.select_next_question(
            clusters=[cluster],
            question_bank=bank,
            user_node_states={},
            importance_lookup={},
            recently_attempted_question_ids=set(),
            now=datetime.now()
        )
        
        assert selected is None
    
    def test_deterministic_tie_breaking(self):
        """Should break ties deterministically by question ID."""
        # Setup graph
        graph = Graph()
        graph.add_node(create_node("node"))
        
        # Setup cluster
        cluster = Cluster(node_ids={"node", "node2"}, seed_node_id="node")
        graph.add_node(create_node("node2"))
        graph.add_edge(create_edge("node", "node2"))
        
        # Setup identical questions (same score)
        bank = QuestionBank()
        q_z = create_question("q_z", ["node"], importance=1.0)
        q_a = create_question("q_a", ["node"], importance=1.0)
        bank.add_question(q_z, graph)
        bank.add_question(q_a, graph)
        
        # Setup user states
        now = datetime.now()
        old_review = now - timedelta(days=30)
        user_states = {
            "node": create_user_state("node", pkr=0.5, last_reviewed=old_review),
        }
        
        # Select multiple times
        selected1 = QuestionRankingEngine.select_next_question(
            clusters=[cluster],
            question_bank=bank,
            user_node_states=user_states,
            importance_lookup={"node": 1.0, "node2": 1.0},
            recently_attempted_question_ids=set(),
            now=now
        )
        
        selected2 = QuestionRankingEngine.select_next_question(
            clusters=[cluster],
            question_bank=bank,
            user_node_states=user_states,
            importance_lookup={"node": 1.0, "node2": 1.0},
            recently_attempted_question_ids=set(),
            now=now
        )
        
        # Should select same question deterministically
        assert selected1.id == selected2.id
        # Should prefer lexicographically first ID
        assert selected1.id == "q_a"
    
    def test_selects_from_multiple_clusters(self):
        """Should consider questions from all clusters."""
        # Setup graph
        graph = Graph()
        graph.add_node(create_node("weak"))
        graph.add_node(create_node("weak2"))
        graph.add_node(create_node("strong"))
        graph.add_node(create_node("strong2"))
        graph.add_edge(create_edge("weak", "weak2"))
        graph.add_edge(create_edge("strong", "strong2"))
        
        # Setup clusters (one weak, one strong)
        cluster_weak = Cluster(node_ids={"weak", "weak2"}, seed_node_id="weak")
        cluster_strong = Cluster(node_ids={"strong", "strong2"}, seed_node_id="strong")
        
        # Setup questions
        bank = QuestionBank()
        q_weak = create_question("q_weak", ["weak"], importance=1.0)
        q_strong = create_question("q_strong", ["strong"], importance=1.0)
        bank.add_question(q_weak, graph)
        bank.add_question(q_strong, graph)
        
        # Setup user states
        now = datetime.now()
        old_review = now - timedelta(days=30)
        user_states = {
            "weak": create_user_state("weak", pkr=0.1, last_reviewed=old_review),
            "weak2": create_user_state("weak2", pkr=0.2, last_reviewed=old_review),
            "strong": create_user_state("strong", pkr=0.9, last_reviewed=now),
            "strong2": create_user_state("strong2", pkr=0.95, last_reviewed=now),
        }
        
        importance = {
            "weak": 1.0,
            "weak2": 1.0,
            "strong": 1.0,
            "strong2": 1.0,
        }
        
        # Select question
        selected = QuestionRankingEngine.select_next_question(
            clusters=[cluster_weak, cluster_strong],
            question_bank=bank,
            user_node_states=user_states,
            importance_lookup=importance,
            recently_attempted_question_ids=set(),
            now=now
        )
        
        # Should select from weak cluster
        assert selected.id == "q_weak"


# ============================================================
# INTEGRATION TESTS
# ============================================================


class TestRankingIntegration:
    """Integration tests for full ranking pipeline."""
    
    def test_full_pipeline(self):
        """Should select best question through full pipeline."""
        # Setup graph
        graph = Graph()
        for node_id in ["python", "variables", "functions", "classes"]:
            graph.add_node(create_node(node_id))
        
        graph.add_edge(create_edge("python", "variables"))
        graph.add_edge(create_edge("variables", "functions"))
        graph.add_edge(create_edge("functions", "classes"))
        
        # Setup clusters
        cluster1 = Cluster(node_ids={"python", "variables"}, seed_node_id="python")
        cluster2 = Cluster(node_ids={"functions", "classes"}, seed_node_id="functions")
        
        # Setup questions
        bank = QuestionBank()
        q1 = create_question("q1", ["python"], importance=1.0, difficulty=1)
        q2 = create_question("q2", ["variables"], importance=2.0, difficulty=2)
        q3 = create_question("q3", ["functions"], importance=1.0, difficulty=3)
        q4 = create_question("q4", ["classes"], importance=5.0, difficulty=4)
        
        bank.add_question(q1, graph)
        bank.add_question(q2, graph)
        bank.add_question(q3, graph)
        bank.add_question(q4, graph)
        
        # Setup user states (python/variables weak, functions/classes strong)
        now = datetime.now()
        old_review = now - timedelta(days=30)
        
        user_states = {
            "python": create_user_state("python", pkr=0.1, last_reviewed=old_review),
            "variables": create_user_state("variables", pkr=0.2, last_reviewed=old_review),
            "functions": create_user_state("functions", pkr=0.8, last_reviewed=now),
            "classes": create_user_state("classes", pkr=0.9, last_reviewed=now),
        }
        
        importance = {node: 1.0 for node in ["python", "variables", "functions", "classes"]}
        
        # Select question
        selected = QuestionRankingEngine.select_next_question(
            clusters=[cluster1, cluster2],
            question_bank=bank,
            user_node_states=user_states,
            importance_lookup=importance,
            recently_attempted_question_ids=set(),
            now=now
        )
        
        # Should select from weak cluster (python/variables)
        assert selected is not None
        assert selected.id in ["q1", "q2"]
        
        # Should prefer higher importance within weak cluster
        assert selected.id == "q2"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
