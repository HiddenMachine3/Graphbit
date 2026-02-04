"""User model representing a learner."""

from pydantic import BaseModel, Field, field_validator


class User(BaseModel):
    """
    Represents a learner in the system.
    
    Users can join communities and have personalized mastery over nodes.
    """
    
    id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    email: str = Field(..., min_length=1)
    joined_community_ids: set[str] = Field(default_factory=set)
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Basic email validation."""
        if '@' not in v or '.' not in v.split('@')[-1]:
            raise ValueError("Invalid email format")
        return v
    
    def join_community(self, community_id: str) -> None:
        """
        Add a community to the user's joined communities.
        
        Args:
            community_id: ID of the community to join
        """
        if not community_id:
            raise ValueError("community_id cannot be empty")
        self.joined_community_ids.add(community_id)
    
    def leave_community(self, community_id: str) -> None:
        """
        Remove a community from the user's joined communities.
        
        Args:
            community_id: ID of the community to leave
            
        Raises:
            ValueError: If user is not in the community
        """
        if community_id not in self.joined_community_ids:
            raise ValueError(f"User is not a member of community '{community_id}'")
        self.joined_community_ids.remove(community_id)
