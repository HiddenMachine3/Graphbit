"""
Phase 7: Revision Session Engine Tests

Comprehensive unit tests for session configuration, session orchestration,
feedback handling, filters, and edge cases.
"""

from datetime import datetime, timedelta
import pytest

from backend.app.domain import (
    # Session
    SessionConfig,
    RevisionSession,
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


def create_node(node_id: str, importance: float = 1.0) -> Node:
    """Helper to create Node."""
    return Node(id=node_id, project_id="test_project_1", topic_name=node_id.capitalize(), importance=importance)


def create_edge(from_id: str, to_id: str) -> Edge:
    """Helper to create Edge."""
    return Edge(
        from_node_id=from_id,
        to_node_id=to_id,
        project_id="test_project_1",
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
        project_id="test_project_1",
        proven_knowledge_rating=pkr,
        stability=stability,
        last_reviewed_at=last_reviewed or datetime.now()
    )


def create_question(
    question_id: str,
    covered_nodes: list[str],
    question_type: QuestionType = QuestionType.FLASHCARD,
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
        project_id="test_project_1",
        text=f"Question {question_id}",
        answer="Answer",
        question_type=question_type,
        knowledge_type=KnowledgeType.CONCEPT,
        covered_node_ids=covered_nodes,
        metadata=metadata,
        difficulty=difficulty
    )


# ============================================================
# SESSION CONFIG TESTS
# ============================================================


class TestSessionConfig:
    """Tests for SessionConfig model."""
    
    def test_create_config_with_max_questions(self):
        """Should create config with max_questions."""
        config = SessionConfig(max_questions=10)
        
        assert config.max_questions == 10
        assert config.allowed_question_types is None
        assert config.allowed_node_ids is None
    
    def test_max_questions_must_be_positive(self):
        """Should reject zero or negative max_questions."""
        with pytest.raises(ValueError):
            SessionConfig(max_questions=0)
        
        with pytest.raises(ValueError):
            SessionConfig(max_questions=-5)
    
    def test_config_with_question_type_filter(self):
        """Should accept question type filter."""
        config = SessionConfig(
            max_questions=5,
            allowed_question_types={QuestionType.FLASHCARD, QuestionType.MCQ}
        )
        
        assert config.allowed_question_types == {QuestionType.FLASHCARD, QuestionType.MCQ}
    
    def test_config_with_node_id_filter(self):
        """Should accept node ID filter."""
        config = SessionConfig(
            max_questions=5,
            allowed_node_ids={"node1", "node2"}
        )
        
        assert config.allowed_node_ids == {"node1", "node2"}
    
    def test_config_converts_list_to_set(self):
        """Should convert lists to sets for filters."""
        config = SessionConfig(
            max_questions=5,
            allowed_question_types=[QuestionType.FLASHCARD],
            allowed_node_ids=["node1", "node2"]
        )
        
        assert isinstance(config.allowed_question_types, set)
        assert isinstance(config.allowed_node_ids, set)


# ============================================================
# SESSION INITIALIZATION TESTS
# ============================================================


class TestRevisionSessionInit:
    """Tests for RevisionSession initialization."""
    
    def test_create_session(self):
        """Should create session with all required inputs."""
        graph = Graph(project_id="test_project_1")
        graph.add_node(create_node("a"))
        
        bank = QuestionBank()
        q1 = create_question("q1", ["a"])
        bank.add_question(q1, graph)
        
        user_states = {
            "a": create_user_state("a", pkr=0.3)
        }
        
        config = SessionConfig(max_questions=5)
        
        session = RevisionSession(
            user_id="user1",
            project_id="test_project_1",
            graph=graph,
            question_bank=bank,
            user_node_states=user_states,
            session_config=config,
        )
        
        assert session.user_id == "user1"
        assert session.answered_count == 0
        assert len(session.asked_question_ids) == 0


# ============================================================
# SESSION LOOP TESTS
# ============================================================


class TestRevisionSessionLoop:
    """Tests for session loop with run_step."""
    
    def test_run_step_returns_question(self):
        """Should return a question when weak nodes exist."""
        # Setup graph
        graph = Graph(project_id="test_project_1")
        graph.add_node(create_node("weak"))
        graph.add_node(create_node("weak2"))
        graph.add_edge(create_edge("weak", "weak2"))
        
        # Setup question bank
        bank = QuestionBank()
        q1 = create_question("q1", ["weak"])
        bank.add_question(q1, graph)
        
        # Setup user states (weak)
        now = datetime.now()
        old_review = now - timedelta(days=30)
        user_states = {
            "weak": create_user_state("weak", pkr=0.1, last_reviewed=old_review),
            "weak2": create_user_state("weak2", pkr=0.2, last_reviewed=old_review),
        }
        
        # Create session
        config = SessionConfig(max_questions=5)
        session = RevisionSession("user1", "test_project_1", graph, bank, user_states, config)
        
        # Run step
        question = session.run_step(now)
        
        assert question is not None
        assert question.id == "q1"
        assert "q1" in session.asked_question_ids
    
    def test_run_step_doesnt_repeat_questions(self):
        """Should not return the same question twice."""
        # Setup graph
        graph = Graph(project_id="test_project_1")
        graph.add_node(create_node("a"))
        graph.add_node(create_node("b"))
        graph.add_edge(create_edge("a", "b"))
        
        # Setup questions
        bank = QuestionBank()
        q1 = create_question("q1", ["a"])
        q2 = create_question("q2", ["a"])
        bank.add_question(q1, graph)
        bank.add_question(q2, graph)
        
        # Setup weak states
        now = datetime.now()
        old = now - timedelta(days=30)
        user_states = {
            "a": create_user_state("a", pkr=0.1, last_reviewed=old),
            "b": create_user_state("b", pkr=0.2, last_reviewed=old),
        }
        
        config = SessionConfig(max_questions=5)
        session = RevisionSession("user1", "test_project_1", graph, bank, user_states, config)
        
        # Get first question
        q_first = session.run_step(now)
        assert q_first is not None
        first_id = q_first.id
        
        # Get second question
        q_second = session.run_step(now)
        assert q_second is not None
        second_id = q_second.id
        
        # Should be different
        assert first_id != second_id
    
    def test_run_step_respects_max_questions(self):
        """Should return None when max_questions reached."""
        # Setup
        graph = Graph(project_id="test_project_1")
        graph.add_node(create_node("a"))
        graph.add_node(create_node("b"))
        graph.add_edge(create_edge("a", "b"))

        bank = QuestionBank()
        q1 = create_question("q1", ["a"])
        bank.add_question(q1, graph)

        now = datetime.now()
        user_states = {
            "a": create_user_state("a", pkr=0.1, last_reviewed=now - timedelta(days=30)),
            "b": create_user_state("b", pkr=0.2, last_reviewed=now - timedelta(days=30))
        }

        config = SessionConfig(max_questions=1)
        session = RevisionSession("user1", "test_project_1", graph, bank, user_states, config)

        # First step should work
        q1 = session.run_step(now)
        assert q1 is not None
        
        # Submit answer to increment count
        session.submit_answer(q1.id, True, now)
        
        # Second step should return None (max reached)
        q2 = session.run_step(now)
        assert q2 is None
    
    def test_run_step_returns_none_when_no_weak_nodes(self):
        """Should return None when all nodes are strong."""
        # Setup
        graph = Graph(project_id="test_project_1")
        graph.add_node(create_node("strong"))
        
        bank = QuestionBank()
        q1 = create_question("q1", ["strong"])
        bank.add_question(q1, graph)
        
        now = datetime.now()
        user_states = {
            "strong": create_user_state("strong", pkr=0.95, last_reviewed=now)
        }
        
        config = SessionConfig(max_questions=5)
        session = RevisionSession("user1", "test_project_1", graph, bank, user_states, config)
        
        # Should return None (no weak nodes)
        question = session.run_step(now)
        assert question is None
    
    def test_run_step_returns_none_when_no_questions_available(self):
        """Should return None when no questions cover weak clusters."""
        # Setup graph with weak nodes
        graph = Graph(project_id="test_project_1")
        graph.add_node(create_node("weak"))
        
        # Empty question bank
        bank = QuestionBank()
        
        now = datetime.now()
        user_states = {
            "weak": create_user_state("weak", pkr=0.1, last_reviewed=now - timedelta(days=30))
        }
        
        config = SessionConfig(max_questions=5)
        session = RevisionSession("user1", "test_project_1", graph, bank, user_states, config)
        
        # Should return None (no questions)
        question = session.run_step(now)
        assert question is None


# ============================================================
# FEEDBACK HANDLING TESTS
# ============================================================


class TestFeedbackHandling:
    """Tests for submit_answer feedback processing."""
    
    def test_submit_correct_answer(self):
        """Should update states when submitting correct answer."""
        # Setup
        graph = Graph(project_id="test_project_1")
        graph.add_node(create_node("a"))
        graph.add_node(create_node("b"))
        graph.add_edge(create_edge("a", "b"))

        bank = QuestionBank()
        q1 = create_question("q1", ["a"])
        bank.add_question(q1, graph)

        now = datetime.now()
        old = now - timedelta(days=30)
        user_states = {
            "a": create_user_state("a", pkr=0.2, last_reviewed=old),
            "b": create_user_state("b", pkr=0.3, last_reviewed=old)
        }
        
        config = SessionConfig(max_questions=5)
        session = RevisionSession("user1", "test_project_1", graph, bank, user_states, config)
        
        # Ask question
        question = session.run_step(now)
        assert question is not None
        
        # Record initial values
        initial_pkr = user_states["a"].proven_knowledge_rating
        initial_hits = question.metadata.hits
        
        # Submit correct answer
        session.submit_answer(question.id, correct=True, timestamp=now)
        
        # Check updates
        assert user_states["a"].proven_knowledge_rating > initial_pkr
        assert question.metadata.hits == initial_hits + 1
        assert question.metadata.misses == 0
        assert question.last_attempted_at == now
        assert session.answered_count == 1
    
    def test_submit_incorrect_answer(self):
        """Should update states when submitting incorrect answer."""
        # Setup
        graph = Graph(project_id="test_project_1")
        graph.add_node(create_node("a"))
        graph.add_node(create_node("b"))
        graph.add_edge(create_edge("a", "b"))

        bank = QuestionBank()
        q1 = create_question("q1", ["a"])
        bank.add_question(q1, graph)

        now = datetime.now()
        user_states = {
            "a": create_user_state("a", pkr=0.2, last_reviewed=now - timedelta(days=30)),
            "b": create_user_state("b", pkr=0.3, last_reviewed=now - timedelta(days=30))
        }
        
        config = SessionConfig(max_questions=5)
        session = RevisionSession("user1", "test_project_1", graph, bank, user_states, config)
        
        # Ask question
        question = session.run_step(now)
        
        # Record initial values
        initial_pkr = user_states["a"].proven_knowledge_rating
        initial_misses = question.metadata.misses
        
        # Submit incorrect answer
        session.submit_answer(question.id, correct=False, timestamp=now)
        
        # Check updates
        assert user_states["a"].proven_knowledge_rating < initial_pkr
        assert question.metadata.misses == initial_misses + 1
        assert question.metadata.hits == 0
        assert session.answered_count == 1
    
    def test_submit_creates_new_user_state_if_missing(self):
        """Should create UserNodeState if doesn't exist."""
        # Setup
        graph = Graph(project_id="test_project_1")
        graph.add_node(create_node("a"))
        graph.add_node(create_node("b"))
        graph.add_node(create_node("c"))
        graph.add_edge(create_edge("a", "b"))
        graph.add_edge(create_edge("b", "c"))  # All connected in chain
        
        bank = QuestionBank()
        # Question covers a and b (both will have states)
        q1 = create_question("q1", ["a", "b"])
        bank.add_question(q1, graph)
        
        now = datetime.now()
        # Only 'a' and 'b' have states (weak), 'c' is just for cluster formation
        user_states = {
            "a": create_user_state("a", pkr=0.1, last_reviewed=now - timedelta(days=30)),
            "b": create_user_state("b", pkr=0.2, last_reviewed=now - timedelta(days=30)),
            "c": create_user_state("c", pkr=0.3, last_reviewed=now - timedelta(days=30))
        }
        
        config = SessionConfig(max_questions=5)
        session = RevisionSession("user1", "test_project_1", graph, bank, user_states, config)
        
        # Ask question and answer - this tests that state updates work
        question = session.run_step(now)
        assert question is not None
        
        # Remove one covered node's state to test creation
        del user_states["b"]
        
        # Now submit answer - should recreate 'b' state
        session.submit_answer(question.id, correct=True, timestamp=now)
        
        # Should have created state for 'b'
        assert "b" in user_states
        assert user_states["b"].user_id == "user1"
        assert user_states["b"].node_id == "b"
        assert user_states["b"].node_id == "b"
    
    def test_submit_answer_raises_error_for_unasked_question(self):
        """Should raise error if question wasn't asked."""
        # Setup
        graph = Graph(project_id="test_project_1")
        graph.add_node(create_node("a"))
        
        bank = QuestionBank()
        q1 = create_question("q1", ["a"])
        bank.add_question(q1, graph)
        
        user_states = {}
        config = SessionConfig(max_questions=5)
        session = RevisionSession("user1", "test_project_1", graph, bank, user_states, config)
        
        # Try to submit without asking
        with pytest.raises(ValueError, match="was not asked"):
            session.submit_answer("q1", True, datetime.now())


# ============================================================
# FILTER TESTS
# ============================================================


class TestSessionFilters:
    """Tests for session filters."""
    
    def test_question_type_filter(self):
        """Should only return questions matching type filter."""
        # Setup graph
        graph = Graph(project_id="test_project_1")
        graph.add_node(create_node("a"))
        graph.add_node(create_node("b"))
        graph.add_edge(create_edge("a", "b"))
        
        # Setup questions with different types
        bank = QuestionBank()
        q_flash = create_question("q_flash", ["a"], question_type=QuestionType.FLASHCARD)
        q_mcq = create_question("q_mcq", ["a"], question_type=QuestionType.MCQ)
        bank.add_question(q_flash, graph)
        bank.add_question(q_mcq, graph)
        
        # Weak state
        now = datetime.now()
        user_states = {
            "a": create_user_state("a", pkr=0.1, last_reviewed=now - timedelta(days=30)),
            "b": create_user_state("b", pkr=0.2, last_reviewed=now - timedelta(days=30)),
        }
        
        # Filter to only FLASHCARD
        config = SessionConfig(
            max_questions=5,
            allowed_question_types={QuestionType.FLASHCARD}
        )
        session = RevisionSession("user1", "test_project_1", graph, bank, user_states, config)
        
        # Should only get flashcard
        question = session.run_step(now)
        assert question is not None
        assert question.question_type == QuestionType.FLASHCARD
    
    def test_node_id_filter(self):
        """Should only return questions covering allowed nodes."""
        # Setup graph
        graph = Graph(project_id="test_project_1")
        graph.add_node(create_node("allowed"))
        graph.add_node(create_node("forbidden"))
        graph.add_node(create_node("helper"))
        graph.add_edge(create_edge("allowed", "helper"))
        graph.add_edge(create_edge("forbidden", "helper"))
        
        # Setup questions
        bank = QuestionBank()
        q_allowed = create_question("q_allowed", ["allowed"])
        q_forbidden = create_question("q_forbidden", ["forbidden"])
        bank.add_question(q_allowed, graph)
        bank.add_question(q_forbidden, graph)
        
        # Make both weak
        now = datetime.now()
        old = now - timedelta(days=30)
        user_states = {
            "allowed": create_user_state("allowed", pkr=0.1, last_reviewed=old),
            "forbidden": create_user_state("forbidden", pkr=0.1, last_reviewed=old),
            "helper": create_user_state("helper", pkr=0.2, last_reviewed=old),
        }
        
        # Filter to only 'allowed'
        config = SessionConfig(
            max_questions=5,
            allowed_node_ids={"allowed"}
        )
        session = RevisionSession("user1", "test_project_1", graph, bank, user_states, config)
        
        # Should only get allowed question
        question = session.run_step(now)
        assert question is not None
        assert "allowed" in question.covered_node_ids
        assert "forbidden" not in question.covered_node_ids
    
    def test_combined_filters(self):
        """Should apply both type and node filters."""
        # Setup
        graph = Graph(project_id="test_project_1")
        graph.add_node(create_node("a"))
        graph.add_node(create_node("b"))
        graph.add_edge(create_edge("a", "b"))
        
        bank = QuestionBank()
        q1 = create_question("q1", ["a"], question_type=QuestionType.FLASHCARD)
        q2 = create_question("q2", ["a"], question_type=QuestionType.MCQ)
        q3 = create_question("q3", ["b"], question_type=QuestionType.FLASHCARD)
        bank.add_question(q1, graph)
        bank.add_question(q2, graph)
        bank.add_question(q3, graph)
        
        now = datetime.now()
        old = now - timedelta(days=30)
        user_states = {
            "a": create_user_state("a", pkr=0.1, last_reviewed=old),
            "b": create_user_state("b", pkr=0.1, last_reviewed=old),
        }
        
        # Filter: FLASHCARD + node 'a'
        config = SessionConfig(
            max_questions=5,
            allowed_question_types={QuestionType.FLASHCARD},
            allowed_node_ids={"a"}
        )
        session = RevisionSession("user1", "test_project_1", graph, bank, user_states, config)
        
        # Should only get q1
        question = session.run_step(now)
        assert question is not None
        assert question.id == "q1"


# ============================================================
# INTEGRATION TESTS
# ============================================================


class TestRevisionSessionIntegration:
    """Integration tests for full session workflow."""
    
    def test_complete_session_workflow(self):
        """Should run complete session from start to finish."""
        # Setup graph
        graph = Graph(project_id="test_project_1")
        for node_id in ["python", "variables", "functions", "loops"]:
            graph.add_node(create_node(node_id))
        
        graph.add_edge(create_edge("python", "variables"))
        graph.add_edge(create_edge("variables", "functions"))
        graph.add_edge(create_edge("functions", "loops"))
        
        # Setup questions
        bank = QuestionBank()
        q1 = create_question("q1", ["python"])
        q2 = create_question("q2", ["variables"])
        q3 = create_question("q3", ["functions"])
        bank.add_question(q1, graph)
        bank.add_question(q2, graph)
        bank.add_question(q3, graph)
        
        # Setup weak states - very weak so they stay weak even after some success
        now = datetime.now()
        old = now - timedelta(days=30)
        user_states = {
            "python": create_user_state("python", pkr=0.1, last_reviewed=old),
            "variables": create_user_state("variables", pkr=0.15, last_reviewed=old),
            "functions": create_user_state("functions", pkr=0.12, last_reviewed=old),
            "loops": create_user_state("loops", pkr=0.9, last_reviewed=now),
        }
        
        # Create session
        config = SessionConfig(max_questions=3)
        session = RevisionSession("user1", "test_project_1", graph, bank, user_states, config)
        
        # Run full session
        questions_asked = []
        
        for i in range(5):  # Try up to 5 times
            q = session.run_step(now + timedelta(minutes=i))
            if q is None:
                break
            
            questions_asked.append(q.id)
            
            # Submit answer (alternating correct/incorrect)
            session.submit_answer(q.id, correct=(i % 2 == 0), timestamp=now + timedelta(minutes=i))
        
        # Should have asked at least 2 questions before running out
        assert len(questions_asked) >= 2
        assert session.answered_count == len(questions_asked)
        
        # Should not repeat questions
        assert len(set(questions_asked)) == len(questions_asked)
        
        # Eventually should stop (either max_questions or no more weak nodes)
        final_q = session.run_step(now + timedelta(minutes=10))
        assert final_q is None or session.answered_count >= config.max_questions
    
    def test_session_adapts_to_feedback(self):
        """Should adapt question selection based on feedback."""
        # Setup simple graph
        graph = Graph(project_id="test_project_1")
        graph.add_node(create_node("weak"))
        graph.add_node(create_node("improving"))
        graph.add_edge(create_edge("weak", "improving"))
        
        # Multiple questions per node
        bank = QuestionBank()
        for i in range(5):
            bank.add_question(create_question(f"q_weak_{i}", ["weak"]), graph)
            bank.add_question(create_question(f"q_improving_{i}", ["improving"]), graph)
        
        # Initial states - both very weak
        now = datetime.now()
        old = now - timedelta(days=30)
        user_states = {
            "weak": create_user_state("weak", pkr=0.1, last_reviewed=old),
            "improving": create_user_state("improving", pkr=0.1, last_reviewed=old),
        }
        
        config = SessionConfig(max_questions=10)
        session = RevisionSession("user1", "test_project_1", graph, bank, user_states, config)
        
        # Get first few questions
        questions = []
        for i in range(5):  # Try up to 5
            q = session.run_step(now + timedelta(minutes=i))
            if q:
                questions.append(q)
                # Answer all correctly to improve PKR
                session.submit_answer(q.id, correct=True, timestamp=now + timedelta(minutes=i))
            else:
                break
        
        # Should have gotten at least 1 question
        assert len(questions) >= 1
        
        # Should not repeat questions
        question_ids = [q.id for q in questions]
        assert len(set(question_ids)) == len(question_ids)
        
        # Questions should cover the weak nodes
        covered_nodes = set()
        for q in questions:
            covered_nodes.update(q.covered_node_ids)
        
        assert len(covered_nodes) > 0


# ============================================================
# EDGE CASES
# ============================================================


class TestEdgeCases:
    """Tests for edge cases and error conditions."""
    
    def test_session_with_single_question(self):
        """Should handle session with only one available question."""
        graph = Graph(project_id="test_project_1")
        graph.add_node(create_node("a"))
        graph.add_node(create_node("b"))
        graph.add_edge(create_edge("a", "b"))

        bank = QuestionBank()
        q1 = create_question("q1", ["a"])
        bank.add_question(q1, graph)

        now = datetime.now()
        user_states = {
            "a": create_user_state("a", pkr=0.1, last_reviewed=now - timedelta(days=30)),
            "b": create_user_state("b", pkr=0.2, last_reviewed=now - timedelta(days=30))
        }

        config = SessionConfig(max_questions=5)
        session = RevisionSession("user1", "test_project_1", graph, bank, user_states, config)
        
        # First step works
        q = session.run_step(now)
        assert q is not None
        assert q.id == "q1"
        
        # Second step returns None (already asked)
        q2 = session.run_step(now)
        assert q2 is None
    
    def test_filter_excludes_all_questions(self):
        """Should return None when filters exclude all questions."""
        graph = Graph(project_id="test_project_1")
        graph.add_node(create_node("a"))
        
        bank = QuestionBank()
        q1 = create_question("q1", ["a"], question_type=QuestionType.FLASHCARD)
        bank.add_question(q1, graph)
        
        now = datetime.now()
        user_states = {
            "a": create_user_state("a", pkr=0.1, last_reviewed=now - timedelta(days=30))
        }
        
        # Filter that excludes the only question
        config = SessionConfig(
            max_questions=5,
            allowed_question_types={QuestionType.MCQ}  # But only FLASHCARD exists
        )
        session = RevisionSession("user1", "test_project_1", graph, bank, user_states, config)
        
        # Should return None (no matching questions)
        q = session.run_step(now)
        assert q is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
