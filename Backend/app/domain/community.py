"""Community model for shared learning groups."""

from pydantic import BaseModel, Field, field_validator


class Community(BaseModel):
    """
    Represents a shared learning group.
    
    Communities reference projects and can define importance overrides
    for nodes and questions within those projects.
    
    Communities do NOT own graphs or questions directly.
    They only apply overrides on top of project content.
    """
    
    id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    description: str = Field(default="")
    project_ids: set[str] = Field(default_factory=set)
    
    # Nested overrides: project_id -> node_id -> importance
    node_importance_overrides: dict[str, dict[str, float]] = Field(default_factory=dict)
    
    # Nested overrides: project_id -> question_id -> importance
    question_importance_overrides: dict[str, dict[str, float]] = Field(default_factory=dict)
    
    @field_validator('node_importance_overrides')
    @classmethod
    def validate_node_importance_overrides(cls, v: dict[str, dict[str, float]]) -> dict[str, dict[str, float]]:
        """Ensure all importance overrides are non-negative."""
        for project_id, node_overrides in v.items():
            for node_id, importance in node_overrides.items():
                if importance < 0:
                    raise ValueError(
                        f"Node importance override for project '{project_id}', "
                        f"node '{node_id}' must be >= 0, got {importance}"
                    )
        return v
    
    @field_validator('question_importance_overrides')
    @classmethod
    def validate_question_importance_overrides(cls, v: dict[str, dict[str, float]]) -> dict[str, dict[str, float]]:
        """Ensure all importance overrides are non-negative."""
        for project_id, question_overrides in v.items():
            for question_id, importance in question_overrides.items():
                if importance < 0:
                    raise ValueError(
                        f"Question importance override for project '{project_id}', "
                        f"question '{question_id}' must be >= 0, got {importance}"
                    )
        return v
    
    def add_project(self, project_id: str) -> None:
        """
        Add a project to this community.
        
        Args:
            project_id: ID of the project to add
            
        Raises:
            ValueError: If project_id is empty
        """
        if not project_id:
            raise ValueError("project_id cannot be empty")
        self.project_ids.add(project_id)
    
    def remove_project(self, project_id: str) -> None:
        """
        Remove a project from this community.
        
        Also removes all associated overrides.
        
        Args:
            project_id: ID of the project to remove
            
        Raises:
            ValueError: If project is not in this community
        """
        if project_id not in self.project_ids:
            raise ValueError(f"Project '{project_id}' is not in this community")
        self.project_ids.remove(project_id)
        
        # Clean up overrides for this project
        self.node_importance_overrides.pop(project_id, None)
        self.question_importance_overrides.pop(project_id, None)
    
    def set_node_importance(self, project_id: str, node_id: str, importance: float) -> None:
        """
        Set or update the importance override for a specific node in a project.
        
        Args:
            project_id: ID of the project
            node_id: ID of the node
            importance: New importance value (must be >= 0)
            
        Raises:
            ValueError: If importance is negative or IDs are empty
        """
        if not project_id:
            raise ValueError("project_id cannot be empty")
        if not node_id:
            raise ValueError("node_id cannot be empty")
        if importance < 0:
            raise ValueError(f"Importance must be >= 0, got {importance}")
        
        if project_id not in self.node_importance_overrides:
            self.node_importance_overrides[project_id] = {}
        self.node_importance_overrides[project_id][node_id] = importance
    
    def remove_node_importance_override(self, project_id: str, node_id: str) -> None:
        """
        Remove the importance override for a specific node in a project.
        
        Args:
            project_id: ID of the project
            node_id: ID of the node
            
        Raises:
            KeyError: If no override exists for this node in this project
        """
        if project_id not in self.node_importance_overrides:
            raise KeyError(f"No overrides found for project '{project_id}'")
        if node_id not in self.node_importance_overrides[project_id]:
            raise KeyError(
                f"No importance override found for node '{node_id}' in project '{project_id}'"
            )
        del self.node_importance_overrides[project_id][node_id]
        
        # Clean up empty project dict
        if not self.node_importance_overrides[project_id]:
            del self.node_importance_overrides[project_id]
    
    def set_question_importance(self, project_id: str, question_id: str, importance: float) -> None:
        """
        Set or update the importance override for a specific question in a project.
        
        Args:
            project_id: ID of the project
            question_id: ID of the question
            importance: New importance value (must be >= 0)
            
        Raises:
            ValueError: If importance is negative or IDs are empty
        """
        if not project_id:
            raise ValueError("project_id cannot be empty")
        if not question_id:
            raise ValueError("question_id cannot be empty")
        if importance < 0:
            raise ValueError(f"Importance must be >= 0, got {importance}")
        
        if project_id not in self.question_importance_overrides:
            self.question_importance_overrides[project_id] = {}
        self.question_importance_overrides[project_id][question_id] = importance
    
    def remove_question_importance_override(self, project_id: str, question_id: str) -> None:
        """
        Remove the importance override for a specific question in a project.
        
        Args:
            project_id: ID of the project
            question_id: ID of the question
            
        Raises:
            KeyError: If no override exists for this question in this project
        """
        if project_id not in self.question_importance_overrides:
            raise KeyError(f"No overrides found for project '{project_id}'")
        if question_id not in self.question_importance_overrides[project_id]:
            raise KeyError(
                f"No importance override found for question '{question_id}' in project '{project_id}'"
            )
        del self.question_importance_overrides[project_id][question_id]
        
        # Clean up empty project dict
        if not self.question_importance_overrides[project_id]:
            del self.question_importance_overrides[project_id]
    
    def get_node_importance(self, project_id: str, node_id: str) -> float | None:
        """
        Get the importance override for a node, if any.
        
        Args:
            project_id: ID of the project
            node_id: ID of the node
            
        Returns:
            Importance override value, or None if no override exists
        """
        return self.node_importance_overrides.get(project_id, {}).get(node_id)
    
    def get_question_importance(self, project_id: str, question_id: str) -> float | None:
        """
        Get the importance override for a question, if any.
        
        Args:
            project_id: ID of the project
            question_id: ID of the question
            
        Returns:
            Importance override value, or None if no override exists
        """
        return self.question_importance_overrides.get(project_id, {}).get(question_id)
