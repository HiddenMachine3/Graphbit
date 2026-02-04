"""Community model for shared learning groups."""

from pydantic import BaseModel, Field, field_validator


class Community(BaseModel):
    """
    Represents a shared learning group.
    
    Communities can define their own knowledge graphs, importance overrides,
    and question sets for collaborative learning.
    """
    
    id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    description: str = Field(default="")
    node_importance_overrides: dict[str, float] = Field(default_factory=dict)
    
    @field_validator('node_importance_overrides')
    @classmethod
    def validate_importance_overrides(cls, v: dict[str, float]) -> dict[str, float]:
        """Ensure all importance overrides are non-negative."""
        for node_id, importance in v.items():
            if importance < 0:
                raise ValueError(
                    f"Importance override for node '{node_id}' must be >= 0, got {importance}"
                )
        return v
    
    def set_node_importance(self, node_id: str, importance: float) -> None:
        """
        Set or update the importance override for a specific node.
        
        Args:
            node_id: ID of the node
            importance: New importance value (must be >= 0)
            
        Raises:
            ValueError: If importance is negative or node_id is empty
        """
        if not node_id:
            raise ValueError("node_id cannot be empty")
        if importance < 0:
            raise ValueError(f"Importance must be >= 0, got {importance}")
        self.node_importance_overrides[node_id] = importance
    
    def remove_node_importance_override(self, node_id: str) -> None:
        """
        Remove the importance override for a specific node.
        
        Args:
            node_id: ID of the node
            
        Raises:
            KeyError: If no override exists for this node
        """
        if node_id not in self.node_importance_overrides:
            raise KeyError(f"No importance override found for node '{node_id}'")
        del self.node_importance_overrides[node_id]
