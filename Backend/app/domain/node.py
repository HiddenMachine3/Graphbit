"""Node model representing a unit of knowledge."""

from pydantic import BaseModel, Field


class Node(BaseModel):
    """
    Represents a single unit of knowledge (concept, fact, skill).
    
    Tracks both proven (system-measured) and user-estimated mastery,
    along with importance, relevance, and engagement metrics.
    """
    
    id: str = Field(..., min_length=1)
    topic_name: str = Field(..., min_length=1)
    proven_knowledge_rating: float = Field(default=0.0, ge=0.0, le=1.0)
    user_estimated_knowledge_rating: float = Field(default=0.0, ge=0.0, le=1.0)
    importance: float = Field(default=0.0, ge=0.0)
    relevance: float = Field(default=0.0, ge=0.0)
    view_frequency: int = Field(default=0, ge=0)
    source_material_ids: set[str] = Field(default_factory=set)
    
    def update_proven_rating(self, new_rating: float) -> None:
        """
        Safely update the proven knowledge rating.
        
        Args:
            new_rating: New rating value (must be between 0.0 and 1.0)
            
        Raises:
            ValueError: If rating is outside [0, 1] range
        """
        if not 0.0 <= new_rating <= 1.0:
            raise ValueError(f"Rating must be between 0.0 and 1.0, got {new_rating}")
        self.proven_knowledge_rating = new_rating
    
    def update_user_estimated_rating(self, new_rating: float) -> None:
        """
        Safely update the user-estimated knowledge rating.
        
        Args:
            new_rating: New rating value (must be between 0.0 and 1.0)
            
        Raises:
            ValueError: If rating is outside [0, 1] range
        """
        if not 0.0 <= new_rating <= 1.0:
            raise ValueError(f"Rating must be between 0.0 and 1.0, got {new_rating}")
        self.user_estimated_knowledge_rating = new_rating
    
    def increment_view_frequency(self) -> None:
        """Increment the view frequency counter by 1."""
        self.view_frequency += 1
