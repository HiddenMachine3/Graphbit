"""Enumeration types for the knowledge graph system."""

from enum import Enum


class EdgeType(str, Enum):
    """Types of relationships between knowledge nodes."""
    PREREQUISITE = "PREREQUISITE"
    DEPENDS_ON = "DEPENDS_ON"
    APPLIED_WITH = "APPLIED_WITH"
    SUBCONCEPT_OF = "SUBCONCEPT_OF"


class QuestionType(str, Enum):
    """Types of active recall questions."""
    FLASHCARD = "FLASHCARD"
    CLOZE = "CLOZE"
    MCQ = "MCQ"
    OPEN = "OPEN"


class KnowledgeType(str, Enum):
    """Categories of knowledge being tested."""
    FACT = "FACT"
    CONCEPT = "CONCEPT"
    PROCEDURE = "PROCEDURE"
