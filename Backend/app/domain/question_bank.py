"""Question bank for managing collections of questions."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from .enums import EdgeType, QuestionType
from .question import Question
from .graph import Graph


class QuestionBank(BaseModel):
    """
    Manages a collection of questions with retrieval and validation.
    
    Provides methods to add, remove, and query questions by various criteria.
    Validates question coverage against a knowledge graph.
    """
    
    questions: dict[str, Question] = Field(default_factory=dict)
    
    def add_question(self, question: Question, graph: Optional[Graph] = None) -> None:
        """
        Add a question to the bank.
        
        Args:
            question: The question to add
            graph: Optional graph for coverage validation
            
        Raises:
            ValueError: If question ID already exists
            ValueError: If coverage validation fails
        """
        if question.id in self.questions:
            raise ValueError(f"Question with id '{question.id}' already exists")
        
        # Validate coverage if graph provided
        if graph is not None:
            # Check all nodes exist
            for node_id in question.covered_node_ids:
                if node_id not in graph.nodes:
                    raise ValueError(f"Node '{node_id}' does not exist in graph")
            
            # Check coverage validity (only if multiple nodes)
            if len(question.covered_node_ids) > 1:
                if not graph.is_valid_coverage(
                    question.covered_node_ids,
                    max_hops=3,
                    allowed_edge_types={EdgeType.PREREQUISITE, EdgeType.DEPENDS_ON, 
                                       EdgeType.APPLIED_WITH, EdgeType.SUBCONCEPT_OF}
                ):
                    raise ValueError(
                        f"Question coverage {question.covered_node_ids} is not valid "
                        "(nodes must be connected within 3 hops)"
                    )
        
        self.questions[question.id] = question
    
    def remove_question(self, question_id: str) -> None:
        """
        Remove a question from the bank.
        
        Args:
            question_id: ID of the question to remove
            
        Raises:
            KeyError: If question doesn't exist
        """
        if question_id not in self.questions:
            raise KeyError(f"Question with id '{question_id}' not found")
        del self.questions[question_id]
    
    def get_question(self, question_id: str) -> Question:
        """
        Retrieve a question by ID.
        
        Args:
            question_id: ID of the question
            
        Returns:
            The question object
            
        Raises:
            KeyError: If question doesn't exist
        """
        if question_id not in self.questions:
            raise KeyError(f"Question with id '{question_id}' not found")
        return self.questions[question_id]
    
    def get_questions_by_node(self, node_id: str) -> list[Question]:
        """
        Get all questions covering a specific node.
        
        Args:
            node_id: ID of the node
            
        Returns:
            List of questions that cover this node
        """
        return [
            q for q in self.questions.values()
            if node_id in q.covered_node_ids
        ]
    
    def get_questions_by_tag(self, tag: str) -> list[Question]:
        """
        Get all questions with a specific tag.
        
        Args:
            tag: The tag to search for
            
        Returns:
            List of questions with this tag
        """
        return [
            q for q in self.questions.values()
            if tag in q.tags
        ]
    
    def get_questions_by_difficulty(
        self, 
        min_difficulty: int = 1, 
        max_difficulty: int = 5
    ) -> list[Question]:
        """
        Get all questions within a difficulty range.
        
        Args:
            min_difficulty: Minimum difficulty (1-5)
            max_difficulty: Maximum difficulty (1-5)
            
        Returns:
            List of questions in the difficulty range
            
        Raises:
            ValueError: If difficulty range is invalid
        """
        if not (1 <= min_difficulty <= 5):
            raise ValueError(f"min_difficulty must be 1-5, got {min_difficulty}")
        if not (1 <= max_difficulty <= 5):
            raise ValueError(f"max_difficulty must be 1-5, got {max_difficulty}")
        if min_difficulty > max_difficulty:
            raise ValueError(
                f"min_difficulty ({min_difficulty}) cannot exceed "
                f"max_difficulty ({max_difficulty})"
            )
        
        return [
            q for q in self.questions.values()
            if min_difficulty <= q.difficulty <= max_difficulty
        ]
    
    def get_questions_by_type(self, question_type: QuestionType) -> list[Question]:
        """
        Get all questions of a specific type.
        
        Args:
            question_type: The question type to filter by
            
        Returns:
            List of questions of this type
        """
        return [
            q for q in self.questions.values()
            if q.question_type == question_type
        ]
    
    def record_question_success(self, question_id: str, timestamp: datetime) -> None:
        """
        Record a successful attempt at a question.
        
        Args:
            question_id: ID of the question
            timestamp: When the attempt occurred
            
        Raises:
            KeyError: If question doesn't exist
        """
        question = self.get_question(question_id)
        question.record_attempt(success=True, timestamp=timestamp)
    
    def record_question_failure(self, question_id: str, timestamp: datetime) -> None:
        """
        Record a failed attempt at a question.
        
        Args:
            question_id: ID of the question
            timestamp: When the attempt occurred
            
        Raises:
            KeyError: If question doesn't exist
        """
        question = self.get_question(question_id)
        question.record_attempt(success=False, timestamp=timestamp)
    
    def count_questions(self) -> int:
        """
        Get the total number of questions in the bank.
        
        Returns:
            Number of questions
        """
        return len(self.questions)
