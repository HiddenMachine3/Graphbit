"""Question models for active recall."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from .enums import QuestionType, KnowledgeType


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
    options: Optional[list[str]] = None
    option_explanations: Optional[dict[str, str]] = None
    difficulty: int = Field(default=3, ge=1, le=5)
    tags: set[str] = Field(default_factory=set)
    last_attempted_at: Optional[datetime] = None
    source_material_ids: set[str] = Field(default_factory=set)
    
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
    
    @field_validator('tags')
    @classmethod
    def validate_tags(cls, v: set[str]) -> set[str]:
        """Ensure all tags are non-empty strings."""
        for tag in v:
            if not tag or not isinstance(tag, str):
                raise ValueError("All tags must be non-empty strings")
        return v

    @field_validator('options')
    @classmethod
    def validate_options(cls, v: Optional[list[str]]) -> Optional[list[str]]:
        """Ensure MCQ options are non-empty strings when provided."""
        if v is None:
            return v
        if not v:
            raise ValueError("options must contain at least one value")
        for option in v:
            if not option or not isinstance(option, str):
                raise ValueError("All options must be non-empty strings")
        return v
    
    def record_hit(self) -> None:
        """Record a correct answer to this question."""
        self.metadata.hits += 1
    
    def record_miss(self) -> None:
        """Record an incorrect answer to this question."""
        self.metadata.misses += 1
    
    def record_attempt(self, success: bool, timestamp: datetime) -> None:
        """
        Record an attempt at this question.
        
        Args:
            success: Whether the answer was correct
            timestamp: When the attempt occurred
        """
        if success:
            self.metadata.hits += 1
        else:
            self.metadata.misses += 1
        self.last_attempted_at = timestamp
    
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
