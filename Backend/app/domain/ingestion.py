"""Content ingestion APIs for creating nodes and questions from materials."""

import csv
from datetime import datetime
from pathlib import Path
from typing import Optional

from .material import MaterialRegistry
from .node import Node
from .question import Question, QuestionMetadata
from .question_bank import QuestionBank
from .graph import Graph
from .enums import QuestionType, KnowledgeType


def create_node_from_material(
    node_id: str,
    topic_name: str,
    material_id: str,
    material_registry: MaterialRegistry,
    importance: float = 0.0,
    relevance: float = 0.0,
) -> Node:
    """
    Create a Node linked to a source material.
    
    Args:
        node_id: Unique identifier for the node
        topic_name: Name of the knowledge topic
        material_id: ID of the source material
        material_registry: Registry to validate material existence
        importance: Importance value (default: 0.0)
        relevance: Relevance value (default: 0.0)
        
    Returns:
        New Node instance linked to the material
        
    Raises:
        KeyError: If material_id doesn't exist in registry
    """
    # Validate material exists
    if not material_registry.has_material(material_id):
        raise KeyError(f"Material with ID '{material_id}' not found in registry")
    
    # Create node with material provenance
    node = Node(
        id=node_id,
        topic_name=topic_name,
        importance=importance,
        relevance=relevance,
        source_material_ids={material_id}
    )
    
    return node


def create_question_from_material(
    question_id: str,
    text: str,
    answer: str,
    covered_node_ids: list[str],
    material_id: str,
    material_registry: MaterialRegistry,
    question_type: QuestionType = QuestionType.FLASHCARD,
    knowledge_type: KnowledgeType = KnowledgeType.CONCEPT,
    difficulty: int = 3,
    tags: Optional[set[str]] = None,
    importance: float = 0.0,
    created_by: str = "system",
) -> Question:
    """
    Create a Question linked to a source material.
    
    Args:
        question_id: Unique identifier for the question
        text: Question text
        answer: Answer text
        covered_node_ids: List of node IDs this question covers
        material_id: ID of the source material
        material_registry: Registry to validate material existence
        question_type: Type of question (default: FLASHCARD)
        knowledge_type: Type of knowledge (default: CONCEPT)
        difficulty: Difficulty level 1-5 (default: 3)
        tags: Optional set of tags
        importance: Importance value (default: 0.0)
        created_by: Creator identifier (default: "system")
        
    Returns:
        New Question instance linked to the material
        
    Raises:
        KeyError: If material_id doesn't exist in registry
    """
    # Validate material exists
    if not material_registry.has_material(material_id):
        raise KeyError(f"Material with ID '{material_id}' not found in registry")
    
    # Create metadata
    metadata = QuestionMetadata(
        created_by=created_by,
        created_at=datetime.now(),
        importance=importance
    )
    
    # Create question with material provenance
    question = Question(
        id=question_id,
        text=text,
        answer=answer,
        question_type=question_type,
        knowledge_type=knowledge_type,
        covered_node_ids=covered_node_ids,
        metadata=metadata,
        difficulty=difficulty,
        tags=tags or set(),
        source_material_ids={material_id}
    )
    
    return question


class CSVQuestionImporter:
    """
    Simple CSV importer for questions.
    
    Expected CSV format:
    - question_text: The question text
    - answer: The answer text
    - covered_node_ids: Comma-separated node IDs
    - difficulty: Integer 1-5
    - tags: Comma-separated tags (optional)
    - question_type: Type of question (optional, defaults to FLASHCARD)
    - knowledge_type: Type of knowledge (optional, defaults to CONCEPT)
    """
    
    def __init__(
        self,
        material_registry: MaterialRegistry,
        question_bank: QuestionBank,
        graph: Graph,
    ):
        """
        Initialize the CSV importer.
        
        Args:
            material_registry: Registry for material validation
            question_bank: Question bank to add questions to
            graph: Graph for coverage validation
        """
        self.material_registry = material_registry
        self.question_bank = question_bank
        self.graph = graph
    
    def import_from_csv(
        self,
        csv_path: str,
        material_id: str,
    ) -> tuple[list[Question], list[tuple[int, str]]]:
        """
        Import questions from a CSV file.
        
        Args:
            csv_path: Path to the CSV file
            material_id: ID of the material representing this CSV
            
        Returns:
            Tuple of (successfully imported questions, list of (row_number, error_message) for failed rows)
            
        Raises:
            KeyError: If material_id doesn't exist in registry
            FileNotFoundError: If CSV file doesn't exist
        """
        # Validate material exists
        if not self.material_registry.has_material(material_id):
            raise KeyError(f"Material with ID '{material_id}' not found in registry")
        
        # Validate file exists
        path = Path(csv_path)
        if not path.exists():
            raise FileNotFoundError(f"CSV file not found: {csv_path}")
        
        imported_questions: list[Question] = []
        errors: list[tuple[int, str]] = []
        
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row_num, row in enumerate(reader, start=2):  # Start at 2 (1 is header)
                try:
                    # Parse required fields
                    question_text = row.get('question_text', '').strip()
                    answer = row.get('answer', '').strip()
                    covered_node_ids_str = row.get('covered_node_ids', '').strip()
                    difficulty_str = row.get('difficulty', '3').strip()
                    
                    # Validate required fields
                    if not question_text:
                        raise ValueError("question_text is required and cannot be empty")
                    if not answer:
                        raise ValueError("answer is required and cannot be empty")
                    if not covered_node_ids_str:
                        raise ValueError("covered_node_ids is required and cannot be empty")
                    
                    # Parse covered node IDs
                    covered_node_ids = [
                        nid.strip() 
                        for nid in covered_node_ids_str.split(',')
                        if nid.strip()
                    ]
                    
                    if not covered_node_ids:
                        raise ValueError("covered_node_ids must contain at least one valid node ID")
                    
                    # Parse difficulty
                    try:
                        difficulty = int(difficulty_str)
                        if not 1 <= difficulty <= 5:
                            raise ValueError("difficulty must be between 1 and 5")
                    except ValueError as e:
                        raise ValueError(f"Invalid difficulty: {e}")
                    
                    # Parse optional tags
                    tags_str = row.get('tags', '').strip()
                    tags = {
                        tag.strip() 
                        for tag in tags_str.split(',')
                        if tag.strip()
                    } if tags_str else set()
                    
                    # Parse optional question type
                    question_type_str = row.get('question_type', 'FLASHCARD').strip().upper()
                    try:
                        question_type = QuestionType[question_type_str]
                    except KeyError:
                        raise ValueError(f"Invalid question_type: {question_type_str}")
                    
                    # Parse optional knowledge type
                    knowledge_type_str = row.get('knowledge_type', 'CONCEPT').strip().upper()
                    try:
                        knowledge_type = KnowledgeType[knowledge_type_str]
                    except KeyError:
                        raise ValueError(f"Invalid knowledge_type: {knowledge_type_str}")
                    
                    # Generate unique question ID
                    question_id = f"csv_{material_id}_q{row_num}"
                    
                    # Create question using ingestion API
                    question = create_question_from_material(
                        question_id=question_id,
                        text=question_text,
                        answer=answer,
                        covered_node_ids=covered_node_ids,
                        material_id=material_id,
                        material_registry=self.material_registry,
                        question_type=question_type,
                        knowledge_type=knowledge_type,
                        difficulty=difficulty,
                        tags=tags,
                        created_by="csv_import"
                    )
                    
                    # Add to question bank (with validation)
                    self.question_bank.add_question(question, self.graph)
                    imported_questions.append(question)
                    
                except Exception as e:
                    # Record error for this row
                    errors.append((row_num, str(e)))
        
        return imported_questions, errors
