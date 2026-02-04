"""Edge model representing relationships between nodes."""

from pydantic import BaseModel, Field, model_validator

from .enums import EdgeType


class Edge(BaseModel):
    """
    Represents a directed relationship between two knowledge nodes.
    
    Defines how nodes relate to each other in the knowledge graph,
    with a weight indicating the strength of the relationship.
    """
    
    from_node_id: str = Field(..., min_length=1)
    to_node_id: str = Field(..., min_length=1)
    weight: float = Field(..., ge=0.0, le=1.0)
    type: EdgeType
    
    @model_validator(mode='after')
    def validate_different_nodes(self) -> 'Edge':
        """Ensure edge connects two different nodes."""
        if self.from_node_id == self.to_node_id:
            raise ValueError("from_node_id and to_node_id must be different")
        return self
