"""Project model - primary owner of knowledge graphs and learning content."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class ProjectVisibility(str, Enum):
    """Access levels for projects."""
    PRIVATE = "private"
    SHARED = "shared"
    PUBLIC = "public"


class Project(BaseModel):
    """
    Represents a project - the primary owner of knowledge graphs, nodes, edges,
    materials, and questions.
    
    Projects are owned by users and can be shared via communities.
    Communities reference projects and can apply importance overrides.
    """
    
    id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    description: str = Field(default="")
    owner_id: str = Field(..., min_length=1)
    visibility: ProjectVisibility = Field(default=ProjectVisibility.PRIVATE)
    created_at: datetime
    updated_at: datetime
    
    def update_metadata(self, name: str | None = None, description: str | None = None) -> None:
        """
        Update project metadata.
        
        Args:
            name: New name (if provided)
            description: New description (if provided)
        """
        if name is not None:
            if not name:
                raise ValueError("Name cannot be empty")
            self.name = name
        if description is not None:
            self.description = description
        self.updated_at = datetime.now()
    
    def set_visibility(self, visibility: ProjectVisibility) -> None:
        """
        Change project visibility.
        
        Args:
            visibility: New visibility level
        """
        self.visibility = visibility
        self.updated_at = datetime.now()
