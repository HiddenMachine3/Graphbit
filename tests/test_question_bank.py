"""
Phase 4: Question Bank & Tagging System Tests

Comprehensive unit tests for question enhancements and question bank management.
"""

from datetime import datetime, timedelta
import pytest
from pydantic import ValidationError

from backend.app.domain import (
    Question,
    QuestionMetadata,
    QuestionType,
    KnowledgeType,
    QuestionBank,
    Graph,
    Node,
    Edge,
    EdgeType,
)


# ============================================================
# TEST HELPERS
# ============================================================


def create_metadata(**kwargs):
    """Helper to create QuestionMetadata with defaults."""
    defaults = {
        "created_by": "test_user",
        "created_at": datetime.now(),
    }
    defaults.update(kwargs)
    return QuestionMetadata(**defaults)


def create_question(question_id="q1", **kwargs):
    """Helper to create Question with defaults."""
    if "metadata" not in kwargs:
        kwargs["metadata"] = create_metadata()
    
    defaults = {
        "id": question_id,
        "text": "Test question",
        "answer": "Test answer",
        "question_type": QuestionType.FLASHCARD,
        "knowledge_type": KnowledgeType.CONCEPT,
        "covered_node_ids": ["node1"],
    }
    defaults.update(kwargs)
    return Question(**defaults)


def create_edge(from_id, to_id, edge_type=EdgeType.PREREQUISITE, weight=1.0):
    """Helper to create Edge with defaults."""
    return Edge(
        from_node_id=from_id,
        to_node_id=to_id,
        type=edge_type,
        weight=weight,
    )


# ============================================================
# QUESTION ENHANCEMENTS TESTS
# ============================================================


class TestQuestionEnhancements:
    """Tests for enhanced Question model fields."""
    
    def test_create_question_with_difficulty(self):
        """Should create question with difficulty field."""
        q = create_question(difficulty=4)
        assert q.difficulty == 4
    
    def test_create_question_with_default_difficulty(self):
        """Should default to difficulty 3."""
        q = create_question()
        assert q.difficulty == 3
    
    def test_difficulty_must_be_in_range(self):
        """Should reject difficulty outside 1-5."""
        with pytest.raises(ValidationError):
            create_question(difficulty=0)
        
        with pytest.raises(ValidationError):
            create_question(difficulty=6)
    
    def test_create_question_with_tags(self):
        """Should create question with tags."""
        q = create_question(tags={"basics", "syntax", "intro"})
        assert q.tags == {"basics", "syntax", "intro"}
    
    def test_create_question_with_empty_tags(self):
        """Should default to empty tag set."""
        q = create_question()
        assert q.tags == set()
    
    def test_tags_must_be_non_empty_strings(self):
        """Should reject empty tag strings."""
        with pytest.raises(ValidationError):
            create_question(tags={"valid", ""})
    
    def test_last_attempted_at_defaults_to_none(self):
        """Should default to None for never attempted."""
        q = create_question()
        assert q.last_attempted_at is None
    
    def test_record_attempt_success(self):
        """Should record successful attempt."""
        q = create_question()
        timestamp = datetime.now()
        q.record_attempt(success=True, timestamp=timestamp)
        
        assert q.metadata.hits == 1
        assert q.metadata.misses == 0
        assert q.last_attempted_at == timestamp
    
    def test_record_attempt_failure(self):
        """Should record failed attempt."""
        q = create_question()
        timestamp = datetime.now()
        q.record_attempt(success=False, timestamp=timestamp)
        
        assert q.metadata.hits == 0
        assert q.metadata.misses == 1
        assert q.last_attempted_at == timestamp
    
    def test_record_multiple_attempts(self):
        """Should track multiple attempts correctly."""
        q = create_question()
        now = datetime.now()
        q.record_attempt(success=True, timestamp=now)
        q.record_attempt(success=False, timestamp=now + timedelta(days=1))
        q.record_attempt(success=True, timestamp=now + timedelta(days=2))
        
        assert q.metadata.hits == 2
        assert q.metadata.misses == 1
        assert q.last_attempted_at == now + timedelta(days=2)


# ============================================================
# QUESTION BANK BASIC OPERATIONS
# ============================================================


class TestQuestionBankBasics:
    """Tests for basic QuestionBank operations."""
    
    def test_create_empty_question_bank(self):
        """Should create empty question bank."""
        bank = QuestionBank()
        
        assert bank.count_questions() == 0
        assert bank.questions == {}
    
    def test_add_question_without_validation(self):
        """Should add question without graph validation."""
        bank = QuestionBank()
        q = create_question()
        
        bank.add_question(q)
        
        assert bank.count_questions() == 1
        assert "q1" in bank.questions
    
    def test_add_duplicate_question_raises_error(self):
        """Should reject duplicate question IDs."""
        bank = QuestionBank()
        q1 = create_question("q1")
        
        bank.add_question(q1)
        
        q2 = create_question("q1", text="Different")
        
        with pytest.raises(ValueError, match="already exists"):
            bank.add_question(q2)
    
    def test_remove_question(self):
        """Should remove question from bank."""
        bank = QuestionBank()
        q = create_question()
        
        bank.add_question(q)
        assert bank.count_questions() == 1
        
        bank.remove_question("q1")
        assert bank.count_questions() == 0
    
    def test_remove_nonexistent_question_raises_error(self):
        """Should raise error when removing nonexistent question."""
        bank = QuestionBank()
        
        with pytest.raises(KeyError, match="not found"):
            bank.remove_question("nonexistent")
    
    def test_get_question(self):
        """Should retrieve question by ID."""
        bank = QuestionBank()
        q = create_question("q1", text="What is Python?")
        
        bank.add_question(q)
        retrieved = bank.get_question("q1")
        
        assert retrieved.id == "q1"
        assert retrieved.text == "What is Python?"
    
    def test_get_nonexistent_question_raises_error(self):
        """Should raise error when getting nonexistent question."""
        bank = QuestionBank()
        
        with pytest.raises(KeyError, match="not found"):
            bank.get_question("nonexistent")


# ============================================================
# COVERAGE VALIDATION TESTS
# ============================================================


class TestCoverageValidation:
    """Tests for question coverage validation against graph."""
    
    def test_add_question_with_valid_single_node(self):
        """Should accept question covering single existing node."""
        graph = Graph()
        graph.add_node(Node(id="python", topic_name="Python"))
        
        bank = QuestionBank()
        q = create_question(covered_node_ids=["python"])
        
        bank.add_question(q, graph=graph)
        assert bank.count_questions() == 1
    
    def test_add_question_with_nonexistent_node_raises_error(self):
        """Should reject question covering nonexistent node."""
        graph = Graph()
        graph.add_node(Node(id="python", topic_name="Python"))
        
        bank = QuestionBank()
        q = create_question(covered_node_ids=["java"])
        
        with pytest.raises(ValueError, match="does not exist in graph"):
            bank.add_question(q, graph=graph)
    
    def test_add_question_with_valid_coverage(self):
        """Should accept question with valid multi-node coverage."""
        graph = Graph()
        graph.add_node(Node(id="python", topic_name="Python"))
        graph.add_node(Node(id="variables", topic_name="Variables"))
        graph.add_edge(create_edge("python", "variables"))
        
        bank = QuestionBank()
        q = create_question(covered_node_ids=["python", "variables"])
        
        bank.add_question(q, graph=graph)
        assert bank.count_questions() == 1
    
    def test_add_question_with_invalid_coverage_raises_error(self):
        """Should reject question with disconnected coverage."""
        graph = Graph()
        graph.add_node(Node(id="python", topic_name="Python"))
        graph.add_node(Node(id="java", topic_name="Java"))
        # No edge between them
        
        bank = QuestionBank()
        q = create_question(covered_node_ids=["python", "java"])
        
        with pytest.raises(ValueError, match="coverage.*is not valid"):
            bank.add_question(q, graph=graph)


# ============================================================
# QUERY TESTS
# ============================================================


class TestQuestionBankQueries:
    """Tests for querying questions by various criteria."""
    
    def test_get_questions_by_node(self):
        """Should retrieve questions covering specific node."""
        bank = QuestionBank()
        
        q1 = create_question("q1", covered_node_ids=["python"])
        q2 = create_question("q2", covered_node_ids=["python", "variables"])
        q3 = create_question("q3", covered_node_ids=["java"])
        
        bank.add_question(q1)
        bank.add_question(q2)
        bank.add_question(q3)
        
        python_questions = bank.get_questions_by_node("python")
        
        assert len(python_questions) == 2
        assert all(q.id in ["q1", "q2"] for q in python_questions)
    
    def test_get_questions_by_tag(self):
        """Should retrieve questions with specific tag."""
        bank = QuestionBank()
        
        q1 = create_question("q1", tags={"basics", "easy"})
        q2 = create_question("q2", tags={"basics", "advanced"})
        q3 = create_question("q3", tags={"advanced"})
        
        bank.add_question(q1)
        bank.add_question(q2)
        bank.add_question(q3)
        
        basics_questions = bank.get_questions_by_tag("basics")
        
        assert len(basics_questions) == 2
        assert all(q.id in ["q1", "q2"] for q in basics_questions)
    
    def test_get_questions_by_difficulty_range(self):
        """Should retrieve questions in difficulty range."""
        bank = QuestionBank()
        
        for i in range(1, 6):
            q = create_question(f"q{i}", difficulty=i)
            bank.add_question(q)
        
        easy_questions = bank.get_questions_by_difficulty(1, 2)
        assert len(easy_questions) == 2
        assert all(q.difficulty <= 2 for q in easy_questions)
        
        medium_questions = bank.get_questions_by_difficulty(3, 3)
        assert len(medium_questions) == 1
        assert medium_questions[0].difficulty == 3
        
        hard_questions = bank.get_questions_by_difficulty(4, 5)
        assert len(hard_questions) == 2
        assert all(q.difficulty >= 4 for q in hard_questions)
    
    def test_get_questions_by_difficulty_invalid_range(self):
        """Should reject invalid difficulty ranges."""
        bank = QuestionBank()
        
        with pytest.raises(ValueError, match="must be 1-5"):
            bank.get_questions_by_difficulty(0, 5)
        
        with pytest.raises(ValueError, match="must be 1-5"):
            bank.get_questions_by_difficulty(1, 6)
        
        with pytest.raises(ValueError, match="cannot exceed"):
            bank.get_questions_by_difficulty(4, 2)
    
    def test_get_questions_by_type(self):
        """Should retrieve questions of specific type."""
        bank = QuestionBank()
        
        q1 = create_question("q1", question_type=QuestionType.FLASHCARD)
        q2 = create_question("q2", question_type=QuestionType.FLASHCARD)
        q3 = create_question("q3", question_type=QuestionType.MCQ)
        
        bank.add_question(q1)
        bank.add_question(q2)
        bank.add_question(q3)
        
        flashcards = bank.get_questions_by_type(QuestionType.FLASHCARD)
        assert len(flashcards) == 2
        
        mcqs = bank.get_questions_by_type(QuestionType.MCQ)
        assert len(mcqs) == 1


# ============================================================
# PERFORMANCE TRACKING TESTS
# ============================================================


class TestPerformanceTracking:
    """Tests for recording question performance."""
    
    def test_record_question_success(self):
        """Should record successful answer."""
        bank = QuestionBank()
        q = create_question()
        
        bank.add_question(q)
        
        timestamp = datetime.now()
        bank.record_question_success("q1", timestamp)
        
        retrieved = bank.get_question("q1")
        assert retrieved.metadata.hits == 1
        assert retrieved.metadata.misses == 0
        assert retrieved.last_attempted_at == timestamp
    
    def test_record_question_failure(self):
        """Should record failed answer."""
        bank = QuestionBank()
        q = create_question()
        
        bank.add_question(q)
        
        timestamp = datetime.now()
        bank.record_question_failure("q1", timestamp)
        
        retrieved = bank.get_question("q1")
        assert retrieved.metadata.hits == 0
        assert retrieved.metadata.misses == 1
        assert retrieved.last_attempted_at == timestamp
    
    def test_record_mixed_performance(self):
        """Should track mixed success and failure."""
        bank = QuestionBank()
        q = create_question()
        
        bank.add_question(q)
        
        now = datetime.now()
        bank.record_question_success("q1", now)
        bank.record_question_failure("q1", now + timedelta(days=1))
        bank.record_question_success("q1", now + timedelta(days=2))
        bank.record_question_success("q1", now + timedelta(days=3))
        
        retrieved = bank.get_question("q1")
        assert retrieved.metadata.hits == 3
        assert retrieved.metadata.misses == 1
        assert retrieved.success_rate == 0.75
    
    def test_record_performance_nonexistent_question(self):
        """Should raise error for nonexistent question."""
        bank = QuestionBank()
        
        with pytest.raises(KeyError):
            bank.record_question_success("nonexistent", datetime.now())
        
        with pytest.raises(KeyError):
            bank.record_question_failure("nonexistent", datetime.now())


# ============================================================
# INTEGRATION TESTS
# ============================================================


class TestQuestionBankIntegration:
    """Integration tests for realistic question bank usage."""
    
    def test_build_python_learning_question_bank(self):
        """Should build complete question bank for Python learning."""
        # Build graph
        graph = Graph()
        graph.add_node(Node(id="python", topic_name="Python Basics"))
        graph.add_node(Node(id="variables", topic_name="Variables"))
        graph.add_node(Node(id="functions", topic_name="Functions"))
        graph.add_node(Node(id="classes", topic_name="Classes"))
        
        graph.add_edge(create_edge("python", "variables"))
        graph.add_edge(create_edge("variables", "functions"))
        graph.add_edge(create_edge("functions", "classes"))
        
        # Build question bank
        bank = QuestionBank()
        
        q1 = create_question(
            "q1",
            text="What is Python?",
            answer="A high-level programming language",
            covered_node_ids=["python"],
            difficulty=1,
            tags={"basics", "intro"},
        )
        
        q2 = create_question(
            "q2",
            text="How do you declare a variable?",
            answer="name = value",
            covered_node_ids=["variables"],
            knowledge_type=KnowledgeType.PROCEDURE,
            difficulty=2,
            tags={"basics", "syntax"},
        )
        
        q3 = create_question(
            "q3",
            text="Define a function in Python",
            answer="def function_name():",
            covered_node_ids=["functions"],
            knowledge_type=KnowledgeType.PROCEDURE,
            difficulty=3,
            tags={"intermediate", "syntax"},
        )
        
        q4 = create_question(
            "q4",
            text="Explain variable scope in functions",
            answer="Variables defined inside have local scope",
            question_type=QuestionType.OPEN,
            covered_node_ids=["variables", "functions"],
            difficulty=4,
            tags={"intermediate", "scope"},
        )
        
        bank.add_question(q1, graph)
        bank.add_question(q2, graph)
        bank.add_question(q3, graph)
        bank.add_question(q4, graph)
        
        assert bank.count_questions() == 4
        
        # Query tests
        basics_questions = bank.get_questions_by_tag("basics")
        assert len(basics_questions) == 2
        
        easy_questions = bank.get_questions_by_difficulty(1, 2)
        assert len(easy_questions) == 2
        
        function_questions = bank.get_questions_by_node("functions")
        assert len(function_questions) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
