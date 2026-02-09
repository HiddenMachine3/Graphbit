"""
Phase 7: Revision Session Engine

Orchestrates weak node clustering (Phase 5) and question ranking (Phase 6)
to run a deterministic revision session with user feedback.
"""

from datetime import datetime
from pydantic import BaseModel, Field, field_validator

from .enums import QuestionType
from .graph import Graph
from .question import Question
from .question_bank import QuestionBank
from .user_knowledge import UserNodeState
from .clustering import WeakNodeDetector, WeakNodeClusterer
from .ranking import QuestionRankingEngine


# ============================================================
# SESSION CONFIGURATION
# ============================================================


class SessionConfig(BaseModel):
    """Configuration for a revision session."""
    
    max_questions: int = Field(gt=0, description="Maximum number of questions in session")
    allowed_question_types: set[QuestionType] | None = Field(
        default=None,
        description="Optional filter for question types. None means all types allowed."
    )
    allowed_node_ids: set[str] | None = Field(
        default=None,
        description="Optional filter for node IDs. None means all nodes allowed."
    )
    
    @field_validator("allowed_question_types", mode="before")
    @classmethod
    def validate_question_types(cls, v):
        """Convert list to set if needed."""
        if v is None:
            return None
        if isinstance(v, list):
            return set(v)
        return v
    
    @field_validator("allowed_node_ids", mode="before")
    @classmethod
    def validate_node_ids(cls, v):
        """Convert list to set if needed."""
        if v is None:
            return None
        if isinstance(v, list):
            return set(v)
        return v


# ============================================================
# REVISION SESSION
# ============================================================


class RevisionSession:
    """
    Manages a single revision session by orchestrating clustering and ranking.
    
    Workflow:
    1. Detect weak nodes (Phase 5)
    2. Generate clusters (Phase 5)
    3. Rank and select question (Phase 6)
    4. Handle user feedback
    5. Update memory state
    """
    
    def __init__(
        self,
        user_id: str,
        project_id: str,
        graph: Graph,
        question_bank: QuestionBank,
        user_node_states: dict[str, UserNodeState],
        session_config: SessionConfig,
    ):
        """
        Initialize a revision session.
        
        Args:
            user_id: User ID
            project_id: Project ID
            graph: Knowledge graph
            question_bank: Question bank
            user_node_states: Current user knowledge states (mutable, will be updated)
            session_config: Session configuration
        """
        self.user_id = user_id
        self.project_id = project_id
        self.graph = graph
        self.question_bank = question_bank
        self.user_node_states = user_node_states
        self.session_config = session_config
        
        # Session state
        self.asked_question_ids: set[str] = set()
        self.answered_count: int = 0
    
    def run_step(self, now: datetime) -> Question | None:
        """
        Execute one step of the revision session: select the next best question.
        
        Uses Phase 5 (clustering) and Phase 6 (ranking) to find the optimal question.
        
        Args:
            now: Current timestamp for forgetting calculations
        
        Returns:
            Next question to ask, or None if session is complete/no valid question exists
        """
        # Check if session is complete
        if self.answered_count >= self.session_config.max_questions:
            return None
        
        # Phase 5: Detect weak nodes and generate clusters
        weak_nodes = WeakNodeDetector.get_weak_nodes(
            user_node_states=list(self.user_node_states.values()),
            now=now,
            importance_lookup=self._get_importance_lookup(),
            weakness_threshold=0.5,  # Standard threshold
        )
        
        if not weak_nodes:
            return None
        
        clusterer = WeakNodeClusterer(
            graph=self.graph,
            max_hops=2,
            allowed_edge_types=None,  # All edge types
        )
        
        clusters = clusterer.generate_clusters(weak_nodes)
        
        if not clusters:
            return None
        
        # Phase 6: Rank and select question
        selected = QuestionRankingEngine.select_next_question(
            clusters=clusters,
            question_bank=self.question_bank,
            user_node_states=self.user_node_states,
            importance_lookup=self._get_importance_lookup(),
            recently_attempted_question_ids=self.asked_question_ids,
            now=now,
        )
        
        if selected is None:
            return None
        
        # Don't return questions already asked in this session
        if selected.id in self.asked_question_ids:
            return None
        
        # Apply filters
        if not self._passes_filters(selected):
            # Try to find another question by temporarily marking this one as asked
            temp_asked = self.asked_question_ids | {selected.id}
            
            selected_alt = QuestionRankingEngine.select_next_question(
                clusters=clusters,
                question_bank=self.question_bank,
                user_node_states=self.user_node_states,
                importance_lookup=self._get_importance_lookup(),
                recently_attempted_question_ids=temp_asked,
                now=now,
            )
            
            # Keep trying until we find a valid question or run out of options
            max_attempts = 100  # Prevent infinite loop
            attempts = 0
            while selected_alt is not None and not self._passes_filters(selected_alt) and attempts < max_attempts:
                temp_asked = temp_asked | {selected_alt.id}
                selected_alt = QuestionRankingEngine.select_next_question(
                    clusters=clusters,
                    question_bank=self.question_bank,
                    user_node_states=self.user_node_states,
                    importance_lookup=self._get_importance_lookup(),
                    recently_attempted_question_ids=temp_asked,
                    now=now,
                )
                attempts += 1
            
            if selected_alt is None or not self._passes_filters(selected_alt):
                return None
            
            selected = selected_alt
        
        # Mark as asked
        self.asked_question_ids.add(selected.id)
        
        return selected
    
    def submit_answer(
        self,
        question_id: str,
        correct: bool,
        timestamp: datetime,
    ) -> None:
        """
        Process user's answer and update all relevant state.
        
        Args:
            question_id: ID of the answered question
            correct: Whether the answer was correct
            timestamp: When the answer was submitted
        
        Raises:
            ValueError: If question wasn't asked or already answered
        """
        # Safety check: question must have been asked
        if question_id not in self.asked_question_ids:
            raise ValueError(f"Question {question_id} was not asked in this session")
        
        # Get the question
        question = self.question_bank.get_question(question_id)
        
        # Update question statistics
        if correct:
            question.record_hit()
        else:
            question.record_miss()
        
        # Update last_attempted_at
        question.last_attempted_at = timestamp
        
        # Update UserNodeState for each covered node
        for node_id in question.covered_node_ids:
            if node_id in self.user_node_states:
                state = self.user_node_states[node_id]
                if correct:
                    state.record_success(timestamp)
                else:
                    state.record_failure(timestamp)
            else:
                # Create new state if doesn't exist
                self.user_node_states[node_id] = UserNodeState(
                    user_id=self.user_id,
                    node_id=node_id,
                    project_id=self.project_id,
                    proven_knowledge_rating=0.5 if correct else 0.3,
                    stability=5.0,
                    last_reviewed_at=timestamp,
                    review_count=1,
                )
        
        # Increment answered count
        self.answered_count += 1
    
    def _get_importance_lookup(self) -> dict[str, float]:
        """
        Build importance lookup from graph nodes.
        
        Returns:
            Dictionary mapping node ID to importance score
        """
        return {node.id: node.importance for node in self.graph.nodes.values()}
    
    def _passes_filters(self, question: Question) -> bool:
        """
        Check if question passes session filters.
        
        Args:
            question: Question to check
        
        Returns:
            True if question passes all filters
        """
        # Check question type filter
        if self.session_config.allowed_question_types is not None:
            if question.question_type not in self.session_config.allowed_question_types:
                return False
        
        # Check node ID filter
        if self.session_config.allowed_node_ids is not None:
            # Question must cover at least one allowed node
            if not any(node_id in self.session_config.allowed_node_ids 
                      for node_id in question.covered_node_ids):
                return False
        
        return True
