"""
Test suite for core domain models.
Validates all business rules, constraints, and behaviors.
"""

from datetime import datetime

import pytest
from pydantic import ValidationError

from backend.app.domain import (
    Community,
    Edge,
    EdgeType,
    Graph,
    KnowledgeType,
    Node,
    Question,
    QuestionMetadata,
    QuestionType,
    User,
)


# ============================================================
# NODE TESTS
# ============================================================


class TestNode:
    """Test Node model validation and behavior."""
    
    def test_create_valid_node(self):
        """Test creating a node with valid data."""
        node = Node(
            id="node1",
            topic_name="Python Basics",
            proven_knowledge_rating=0.7,
            user_estimated_knowledge_rating=0.8,
            importance=5.0,
            relevance=3.0,
            view_frequency=10,
        )
        
        assert node.id == "node1"
        assert node.topic_name == "Python Basics"
        assert node.proven_knowledge_rating == 0.7
        assert node.user_estimated_knowledge_rating == 0.8
        assert node.importance == 5.0
        assert node.relevance == 3.0
        assert node.view_frequency == 10
    
    def test_node_with_defaults(self):
        """Test node creation with default values."""
        node = Node(id="node1", topic_name="Topic")
        
        assert node.proven_knowledge_rating == 0.0
        assert node.user_estimated_knowledge_rating == 0.0
        assert node.importance == 0.0
        assert node.relevance == 0.0
        assert node.view_frequency == 0
    
    def test_node_id_cannot_be_empty(self):
        """Test that node ID must be non-empty."""
        with pytest.raises(ValidationError):
            Node(id="", topic_name="Topic")
    
    def test_node_topic_name_cannot_be_empty(self):
        """Test that topic name must be non-empty."""
        with pytest.raises(ValidationError):
            Node(id="node1", topic_name="")
    
    def test_proven_rating_must_be_in_range(self):
        """Test proven rating must be between 0 and 1."""
        with pytest.raises(ValidationError):
            Node(id="node1", topic_name="Topic", proven_knowledge_rating=1.5)
        
        with pytest.raises(ValidationError):
            Node(id="node1", topic_name="Topic", proven_knowledge_rating=-0.1)
    
    def test_user_estimated_rating_must_be_in_range(self):
        """Test user estimated rating must be between 0 and 1."""
        with pytest.raises(ValidationError):
            Node(id="node1", topic_name="Topic", user_estimated_knowledge_rating=1.5)
        
        with pytest.raises(ValidationError):
            Node(id="node1", topic_name="Topic", user_estimated_knowledge_rating=-0.1)
    
    def test_importance_cannot_be_negative(self):
        """Test importance must be non-negative."""
        with pytest.raises(ValidationError):
            Node(id="node1", topic_name="Topic", importance=-1.0)
    
    def test_relevance_cannot_be_negative(self):
        """Test relevance must be non-negative."""
        with pytest.raises(ValidationError):
            Node(id="node1", topic_name="Topic", relevance=-1.0)
    
    def test_view_frequency_cannot_be_negative(self):
        """Test view frequency must be non-negative."""
        with pytest.raises(ValidationError):
            Node(id="node1", topic_name="Topic", view_frequency=-1)
    
    def test_update_proven_rating_valid(self):
        """Test safely updating proven rating."""
        node = Node(id="node1", topic_name="Topic")
        node.update_proven_rating(0.9)
        assert node.proven_knowledge_rating == 0.9
    
    def test_update_proven_rating_invalid(self):
        """Test updating proven rating with invalid value."""
        node = Node(id="node1", topic_name="Topic")
        
        with pytest.raises(ValueError):
            node.update_proven_rating(1.5)
        
        with pytest.raises(ValueError):
            node.update_proven_rating(-0.1)
    
    def test_update_user_estimated_rating_valid(self):
        """Test safely updating user estimated rating."""
        node = Node(id="node1", topic_name="Topic")
        node.update_user_estimated_rating(0.6)
        assert node.user_estimated_knowledge_rating == 0.6
    
    def test_update_user_estimated_rating_invalid(self):
        """Test updating user estimated rating with invalid value."""
        node = Node(id="node1", topic_name="Topic")
        
        with pytest.raises(ValueError):
            node.update_user_estimated_rating(2.0)
        
        with pytest.raises(ValueError):
            node.update_user_estimated_rating(-0.5)
    
    def test_increment_view_frequency(self):
        """Test incrementing view frequency."""
        node = Node(id="node1", topic_name="Topic", view_frequency=5)
        node.increment_view_frequency()
        assert node.view_frequency == 6
        
        node.increment_view_frequency()
        assert node.view_frequency == 7


# ============================================================
# EDGE TESTS
# ============================================================


class TestEdge:
    """Test Edge model validation and behavior."""
    
    def test_create_valid_edge(self):
        """Test creating an edge with valid data."""
        edge = Edge(
            from_node_id="node1",
            to_node_id="node2",
            weight=0.8,
            type=EdgeType.PREREQUISITE,
        )
        
        assert edge.from_node_id == "node1"
        assert edge.to_node_id == "node2"
        assert edge.weight == 0.8
        assert edge.type == EdgeType.PREREQUISITE
    
    def test_edge_types(self):
        """Test all edge types are valid."""
        for edge_type in EdgeType:
            edge = Edge(
                from_node_id="node1",
                to_node_id="node2",
                weight=0.5,
                type=edge_type,
            )
            assert edge.type == edge_type
    
    def test_weight_must_be_in_range(self):
        """Test edge weight must be between 0 and 1."""
        with pytest.raises(ValidationError):
            Edge(
                from_node_id="node1",
                to_node_id="node2",
                weight=1.5,
                type=EdgeType.DEPENDS_ON,
            )
        
        with pytest.raises(ValidationError):
            Edge(
                from_node_id="node1",
                to_node_id="node2",
                weight=-0.1,
                type=EdgeType.DEPENDS_ON,
            )
    
    def test_from_and_to_must_be_different(self):
        """Test that from_node_id and to_node_id must be different."""
        with pytest.raises(ValidationError, match="must be different"):
            Edge(
                from_node_id="node1",
                to_node_id="node1",
                weight=0.5,
                type=EdgeType.APPLIED_WITH,
            )


# ============================================================
# GRAPH TESTS
# ============================================================


class TestGraph:
    """Test Graph model validation and behavior."""
    
    def test_create_empty_graph(self):
        """Test creating an empty graph."""
        graph = Graph()
        assert len(graph.nodes) == 0
        assert len(graph.edges) == 0
    
    def test_add_node(self):
        """Test adding a node to the graph."""
        graph = Graph()
        node = Node(id="node1", topic_name="Topic 1")
        
        graph.add_node(node)
        assert "node1" in graph.nodes
        assert graph.nodes["node1"] == node
    
    def test_add_duplicate_node(self):
        """Test that adding duplicate node raises error."""
        graph = Graph()
        node1 = Node(id="node1", topic_name="Topic 1")
        node2 = Node(id="node1", topic_name="Topic 2")
        
        graph.add_node(node1)
        with pytest.raises(ValueError, match="already exists"):
            graph.add_node(node2)
    
    def test_remove_node(self):
        """Test removing a node from the graph."""
        graph = Graph()
        node = Node(id="node1", topic_name="Topic 1")
        graph.add_node(node)
        
        graph.remove_node("node1")
        assert "node1" not in graph.nodes
    
    def test_remove_nonexistent_node(self):
        """Test removing a node that doesn't exist."""
        graph = Graph()
        with pytest.raises(KeyError, match="not found"):
            graph.remove_node("nonexistent")
    
    def test_add_edge(self):
        """Test adding an edge to the graph."""
        graph = Graph()
        node1 = Node(id="node1", topic_name="Topic 1")
        node2 = Node(id="node2", topic_name="Topic 2")
        graph.add_node(node1)
        graph.add_node(node2)
        
        edge = Edge(
            from_node_id="node1",
            to_node_id="node2",
            weight=0.7,
            type=EdgeType.PREREQUISITE,
        )
        
        graph.add_edge(edge)
        assert len(graph.edges) == 1
        assert graph.edges[0] == edge
    
    def test_add_edge_with_nonexistent_from_node(self):
        """Test adding edge with non-existent from_node."""
        graph = Graph()
        node2 = Node(id="node2", topic_name="Topic 2")
        graph.add_node(node2)
        
        edge = Edge(
            from_node_id="nonexistent",
            to_node_id="node2",
            weight=0.7,
            type=EdgeType.PREREQUISITE,
        )
        
        with pytest.raises(ValueError, match="from_node_id.*not found"):
            graph.add_edge(edge)
    
    def test_add_edge_with_nonexistent_to_node(self):
        """Test adding edge with non-existent to_node."""
        graph = Graph()
        node1 = Node(id="node1", topic_name="Topic 1")
        graph.add_node(node1)
        
        edge = Edge(
            from_node_id="node1",
            to_node_id="nonexistent",
            weight=0.7,
            type=EdgeType.PREREQUISITE,
        )
        
        with pytest.raises(ValueError, match="to_node_id.*not found"):
            graph.add_edge(edge)
    
    def test_remove_edge(self):
        """Test removing an edge from the graph."""
        graph = Graph()
        node1 = Node(id="node1", topic_name="Topic 1")
        node2 = Node(id="node2", topic_name="Topic 2")
        graph.add_node(node1)
        graph.add_node(node2)
        
        edge = Edge(
            from_node_id="node1",
            to_node_id="node2",
            weight=0.7,
            type=EdgeType.PREREQUISITE,
        )
        graph.add_edge(edge)
        
        graph.remove_edge("node1", "node2")
        assert len(graph.edges) == 0
    
    def test_remove_nonexistent_edge(self):
        """Test removing an edge that doesn't exist."""
        graph = Graph()
        with pytest.raises(ValueError, match="No edge found"):
            graph.remove_edge("node1", "node2")
    
    def test_remove_node_removes_connected_edges(self):
        """Test that removing a node also removes its edges."""
        graph = Graph()
        node1 = Node(id="node1", topic_name="Topic 1")
        node2 = Node(id="node2", topic_name="Topic 2")
        node3 = Node(id="node3", topic_name="Topic 3")
        graph.add_node(node1)
        graph.add_node(node2)
        graph.add_node(node3)
        
        edge1 = Edge(
            from_node_id="node1",
            to_node_id="node2",
            weight=0.7,
            type=EdgeType.PREREQUISITE,
        )
        edge2 = Edge(
            from_node_id="node2",
            to_node_id="node3",
            weight=0.5,
            type=EdgeType.DEPENDS_ON,
        )
        edge3 = Edge(
            from_node_id="node1",
            to_node_id="node3",
            weight=0.3,
            type=EdgeType.APPLIED_WITH,
        )
        
        graph.add_edge(edge1)
        graph.add_edge(edge2)
        graph.add_edge(edge3)
        assert len(graph.edges) == 3
        
        # Remove node2 should remove edge1 and edge2
        graph.remove_node("node2")
        assert len(graph.edges) == 1
        assert graph.edges[0] == edge3


# ============================================================
# QUESTION TESTS
# ============================================================


class TestQuestion:
    """Test Question model validation and behavior."""
    
    def test_create_valid_question(self):
        """Test creating a question with valid data."""
        metadata = QuestionMetadata(
            created_by="user1",
            created_at=datetime.now(),
            importance=5.0,
            hits=10,
            misses=2,
        )
        
        question = Question(
            id="q1",
            text="What is Python?",
            answer="A programming language",
            question_type=QuestionType.FLASHCARD,
            knowledge_type=KnowledgeType.CONCEPT,
            covered_node_ids=["node1", "node2"],
            metadata=metadata,
        )
        
        assert question.id == "q1"
        assert question.text == "What is Python?"
        assert question.answer == "A programming language"
        assert question.question_type == QuestionType.FLASHCARD
        assert question.knowledge_type == KnowledgeType.CONCEPT
        assert question.covered_node_ids == ["node1", "node2"]
        assert question.metadata.hits == 10
        assert question.metadata.misses == 2
    
    def test_covered_node_ids_cannot_be_empty(self):
        """Test that covered_node_ids must contain at least one node."""
        metadata = QuestionMetadata(
            created_by="user1",
            created_at=datetime.now(),
        )
        
        with pytest.raises(ValidationError):
            Question(
                id="q1",
                text="What is Python?",
                answer="A programming language",
                question_type=QuestionType.FLASHCARD,
                knowledge_type=KnowledgeType.CONCEPT,
                covered_node_ids=[],
                metadata=metadata,
            )
    
    def test_metadata_importance_cannot_be_negative(self):
        """Test metadata importance must be non-negative."""
        with pytest.raises(ValidationError):
            QuestionMetadata(
                created_by="user1",
                created_at=datetime.now(),
                importance=-1.0,
            )
    
    def test_metadata_hits_cannot_be_negative(self):
        """Test metadata hits must be non-negative."""
        with pytest.raises(ValidationError):
            QuestionMetadata(
                created_by="user1",
                created_at=datetime.now(),
                hits=-1,
            )
    
    def test_metadata_misses_cannot_be_negative(self):
        """Test metadata misses must be non-negative."""
        with pytest.raises(ValidationError):
            QuestionMetadata(
                created_by="user1",
                created_at=datetime.now(),
                misses=-1,
            )
    
    def test_record_hit(self):
        """Test recording a correct answer."""
        metadata = QuestionMetadata(
            created_by="user1",
            created_at=datetime.now(),
            hits=5,
            misses=2,
        )
        
        question = Question(
            id="q1",
            text="What is Python?",
            answer="A programming language",
            question_type=QuestionType.FLASHCARD,
            knowledge_type=KnowledgeType.CONCEPT,
            covered_node_ids=["node1"],
            metadata=metadata,
        )
        
        question.record_hit()
        assert question.metadata.hits == 6
        assert question.metadata.misses == 2
    
    def test_record_miss(self):
        """Test recording an incorrect answer."""
        metadata = QuestionMetadata(
            created_by="user1",
            created_at=datetime.now(),
            hits=5,
            misses=2,
        )
        
        question = Question(
            id="q1",
            text="What is Python?",
            answer="A programming language",
            question_type=QuestionType.FLASHCARD,
            knowledge_type=KnowledgeType.CONCEPT,
            covered_node_ids=["node1"],
            metadata=metadata,
        )
        
        question.record_miss()
        assert question.metadata.hits == 5
        assert question.metadata.misses == 3
    
    def test_success_rate_calculation(self):
        """Test success rate calculation."""
        metadata = QuestionMetadata(
            created_by="user1",
            created_at=datetime.now(),
            hits=8,
            misses=2,
        )
        
        question = Question(
            id="q1",
            text="What is Python?",
            answer="A programming language",
            question_type=QuestionType.FLASHCARD,
            knowledge_type=KnowledgeType.CONCEPT,
            covered_node_ids=["node1"],
            metadata=metadata,
        )
        
        assert question.success_rate == 0.8
    
    def test_success_rate_with_no_attempts(self):
        """Test success rate returns None when no attempts."""
        metadata = QuestionMetadata(
            created_by="user1",
            created_at=datetime.now(),
            hits=0,
            misses=0,
        )
        
        question = Question(
            id="q1",
            text="What is Python?",
            answer="A programming language",
            question_type=QuestionType.FLASHCARD,
            knowledge_type=KnowledgeType.CONCEPT,
            covered_node_ids=["node1"],
            metadata=metadata,
        )
        
        assert question.success_rate is None
    
    def test_all_question_types(self):
        """Test all question types are valid."""
        metadata = QuestionMetadata(
            created_by="user1",
            created_at=datetime.now(),
        )
        
        for question_type in QuestionType:
            question = Question(
                id=f"q_{question_type}",
                text="Test question",
                answer="Test answer",
                question_type=question_type,
                knowledge_type=KnowledgeType.FACT,
                covered_node_ids=["node1"],
                metadata=metadata,
            )
            assert question.question_type == question_type
    
    def test_all_knowledge_types(self):
        """Test all knowledge types are valid."""
        metadata = QuestionMetadata(
            created_by="user1",
            created_at=datetime.now(),
        )
        
        for knowledge_type in KnowledgeType:
            question = Question(
                id=f"q_{knowledge_type}",
                text="Test question",
                answer="Test answer",
                question_type=QuestionType.FLASHCARD,
                knowledge_type=knowledge_type,
                covered_node_ids=["node1"],
                metadata=metadata,
            )
            assert question.knowledge_type == knowledge_type


# ============================================================
# USER TESTS
# ============================================================


class TestUser:
    """Test User model validation and behavior."""
    
    def test_create_valid_user(self):
        """Test creating a user with valid data."""
        user = User(
            id="user1",
            name="John Doe",
            email="john@example.com",
            joined_community_ids={"community1", "community2"},
        )
        
        assert user.id == "user1"
        assert user.name == "John Doe"
        assert user.email == "john@example.com"
        assert "community1" in user.joined_community_ids
        assert "community2" in user.joined_community_ids
    
    def test_user_with_default_communities(self):
        """Test user creation with default empty communities."""
        user = User(id="user1", name="John Doe", email="john@example.com")
        assert len(user.joined_community_ids) == 0
    
    def test_email_validation_missing_at(self):
        """Test email validation requires @ symbol."""
        with pytest.raises(ValidationError, match="Invalid email"):
            User(id="user1", name="John Doe", email="invalid.email.com")
    
    def test_email_validation_missing_domain(self):
        """Test email validation requires domain."""
        with pytest.raises(ValidationError, match="Invalid email"):
            User(id="user1", name="John Doe", email="user@")
    
    def test_join_community(self):
        """Test joining a community."""
        user = User(id="user1", name="John Doe", email="john@example.com")
        user.join_community("community1")
        
        assert "community1" in user.joined_community_ids
    
    def test_join_community_empty_id(self):
        """Test joining community with empty ID raises error."""
        user = User(id="user1", name="John Doe", email="john@example.com")
        with pytest.raises(ValueError, match="cannot be empty"):
            user.join_community("")
    
    def test_join_multiple_communities(self):
        """Test joining multiple communities."""
        user = User(id="user1", name="John Doe", email="john@example.com")
        user.join_community("community1")
        user.join_community("community2")
        
        assert "community1" in user.joined_community_ids
        assert "community2" in user.joined_community_ids
        assert len(user.joined_community_ids) == 2
    
    def test_join_same_community_twice(self):
        """Test joining same community twice (set behavior)."""
        user = User(id="user1", name="John Doe", email="john@example.com")
        user.join_community("community1")
        user.join_community("community1")
        
        assert len(user.joined_community_ids) == 1
    
    def test_leave_community(self):
        """Test leaving a community."""
        user = User(
            id="user1",
            name="John Doe",
            email="john@example.com",
            joined_community_ids={"community1", "community2"},
        )
        
        user.leave_community("community1")
        assert "community1" not in user.joined_community_ids
        assert "community2" in user.joined_community_ids
    
    def test_leave_community_not_member(self):
        """Test leaving a community user is not a member of."""
        user = User(id="user1", name="John Doe", email="john@example.com")
        
        with pytest.raises(ValueError, match="not a member"):
            user.leave_community("community1")


# ============================================================
# COMMUNITY TESTS
# ============================================================


class TestCommunity:
    """Test Community model validation and behavior."""
    
    def test_create_valid_community(self):
        """Test creating a community with valid data."""
        community = Community(
            id="comm1",
            name="Python Learners",
            description="A community for Python enthusiasts",
            node_importance_overrides={"node1": 10.0, "node2": 5.0},
        )
        
        assert community.id == "comm1"
        assert community.name == "Python Learners"
        assert community.description == "A community for Python enthusiasts"
        assert community.node_importance_overrides["node1"] == 10.0
        assert community.node_importance_overrides["node2"] == 5.0
    
    def test_community_with_defaults(self):
        """Test community creation with default values."""
        community = Community(id="comm1", name="Python Learners")
        
        assert community.description == ""
        assert len(community.node_importance_overrides) == 0
    
    def test_importance_overrides_cannot_be_negative(self):
        """Test importance overrides must be non-negative."""
        with pytest.raises(ValidationError, match="must be >= 0"):
            Community(
                id="comm1",
                name="Python Learners",
                node_importance_overrides={"node1": -5.0},
            )
    
    def test_set_node_importance(self):
        """Test setting node importance override."""
        community = Community(id="comm1", name="Python Learners")
        community.set_node_importance("node1", 8.0)
        
        assert community.node_importance_overrides["node1"] == 8.0
    
    def test_set_node_importance_negative(self):
        """Test setting negative importance raises error."""
        community = Community(id="comm1", name="Python Learners")
        
        with pytest.raises(ValueError, match="must be >= 0"):
            community.set_node_importance("node1", -3.0)
    
    def test_set_node_importance_empty_id(self):
        """Test setting importance with empty node ID raises error."""
        community = Community(id="comm1", name="Python Learners")
        
        with pytest.raises(ValueError, match="cannot be empty"):
            community.set_node_importance("", 5.0)
    
    def test_update_existing_node_importance(self):
        """Test updating an existing node importance override."""
        community = Community(
            id="comm1",
            name="Python Learners",
            node_importance_overrides={"node1": 5.0},
        )
        
        community.set_node_importance("node1", 10.0)
        assert community.node_importance_overrides["node1"] == 10.0
    
    def test_remove_node_importance_override(self):
        """Test removing node importance override."""
        community = Community(
            id="comm1",
            name="Python Learners",
            node_importance_overrides={"node1": 5.0, "node2": 8.0},
        )
        
        community.remove_node_importance_override("node1")
        assert "node1" not in community.node_importance_overrides
        assert "node2" in community.node_importance_overrides
    
    def test_remove_nonexistent_importance_override(self):
        """Test removing non-existent importance override raises error."""
        community = Community(id="comm1", name="Python Learners")
        
        with pytest.raises(KeyError, match="No importance override found"):
            community.remove_node_importance_override("node1")
