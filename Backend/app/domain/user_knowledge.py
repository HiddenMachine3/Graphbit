"""User knowledge state tracking with forgetting model."""

import math
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


# Learning rate constants for review updates
SUCCESS_PKR_GAIN = 0.15
SUCCESS_STABILITY_GAIN = 1.2
FAILURE_PKR_LOSS = 0.20
FAILURE_STABILITY_LOSS = 0.8
MIN_STABILITY = 0.1
MAX_STABILITY = 10.0


class UserNodeState(BaseModel):
    """
    Represents a user's mastery of a specific knowledge node.
    
    Tracks proven knowledge rating (PKR), review history, and stability
    to model learning and forgetting over time.
    """
    
    user_id: str = Field(..., min_length=1)
    project_id: str = Field(..., min_length=1)
    node_id: str = Field(..., min_length=1)
    proven_knowledge_rating: float = Field(default=0.0, ge=0.0, le=1.0)
    review_count: int = Field(default=0, ge=0)
    last_reviewed_at: Optional[datetime] = None
    stability: float = Field(default=1.0, gt=0)
    
    @field_validator('stability')
    @classmethod
    def validate_stability(cls, v: float) -> float:
        """Ensure stability is positive."""
        if v <= 0:
            raise ValueError(f"Stability must be > 0, got {v}")
        return v
    
    def record_success(self, timestamp: datetime) -> None:
        """
        Record a successful review (correct answer).
        
        Increases PKR and stability, updates review count and timestamp.
        
        Args:
            timestamp: When the review occurred
        """
        # Increase PKR with diminishing returns
        self.proven_knowledge_rating = min(
            1.0,
            self.proven_knowledge_rating + SUCCESS_PKR_GAIN * (1 - self.proven_knowledge_rating)
        )
        
        # Increase stability (memory consolidation)
        self.stability = min(
            MAX_STABILITY,
            self.stability * SUCCESS_STABILITY_GAIN
        )
        
        # Update metadata
        self.review_count += 1
        self.last_reviewed_at = timestamp
    
    def record_failure(self, timestamp: datetime) -> None:
        """
        Record a failed review (incorrect answer).
        
        Decreases PKR and stability, updates review count and timestamp.
        
        Args:
            timestamp: When the review occurred
        """
        # Decrease PKR proportionally
        self.proven_knowledge_rating = max(
            0.0,
            self.proven_knowledge_rating - FAILURE_PKR_LOSS * self.proven_knowledge_rating
        )
        
        # Decrease stability (memory weakening)
        self.stability = max(
            MIN_STABILITY,
            self.stability * FAILURE_STABILITY_LOSS
        )
        
        # Update metadata
        self.review_count += 1
        self.last_reviewed_at = timestamp
    
    def forgetting_score(self, now: datetime) -> float:
        """
        Calculate how much knowledge has been forgotten since last review.
        
        Uses exponential decay based on time elapsed and stability.
        
        Args:
            now: Current timestamp
            
        Returns:
            Forgetting score in [0, 1], where:
            - 0.0 = no forgetting (just reviewed)
            - 1.0 = maximum forgetting (never reviewed or very old)
        """
        # If never reviewed, maximum forgetting
        if self.last_reviewed_at is None:
            return 1.0
        
        # Calculate time elapsed in days
        elapsed = now - self.last_reviewed_at
        days_elapsed = elapsed.total_seconds() / (24 * 3600)
        
        # Exponential decay: higher stability means slower forgetting
        # Formula: 1 - e^(-days / stability)
        # This gives a value in [0, 1] that increases over time
        decay = 1.0 - math.exp(-days_elapsed / self.stability)
        
        return min(1.0, max(0.0, decay))
    
    def weakness_score(self, now: datetime, importance: float) -> float:
        """
        Calculate overall weakness score for this node.
        
        Combines low PKR, high forgetting, and importance to determine
        which topics need the most attention.
        
        Args:
            now: Current timestamp
            importance: Node importance value (>= 0)
            
        Returns:
            Weakness score (unbounded, higher = weaker)
            
        Raises:
            ValueError: If importance is negative
        """
        if importance < 0:
            raise ValueError(f"Importance must be >= 0, got {importance}")
        
        # Component 1: Low knowledge (1 - PKR)
        knowledge_weakness = 1.0 - self.proven_knowledge_rating
        
        # Component 2: Forgetting
        forgetting = self.forgetting_score(now)
        
        # Component 3: Combined weakness (knowledge gap + forgetting)
        # Average of the two components
        base_weakness = (knowledge_weakness + forgetting) / 2.0
        
        # Component 4: Importance amplification
        # Higher importance increases urgency
        importance_factor = 1.0 + (importance / 10.0)
        
        # Final weakness score
        weakness = base_weakness * importance_factor
        
        return weakness
