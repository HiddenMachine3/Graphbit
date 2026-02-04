"""Material model for content ingestion and provenance tracking."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class MaterialType(str, Enum):
    """Types of learning materials that can be ingested."""
    TEXT = "TEXT"
    PDF = "PDF"
    VIDEO = "VIDEO"
    WEB = "WEB"
    CSV = "CSV"


class Material(BaseModel):
    """
    Represents a source material from which knowledge nodes and questions are created.
    
    Tracks provenance of content to maintain transparency about where knowledge
    in the system originates.
    """
    
    id: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    material_type: MaterialType
    source: str = Field(..., min_length=1)  # URL or file path
    created_at: datetime
    metadata: dict[str, str] = Field(default_factory=dict)


class MaterialRegistry:
    """
    Registry for storing and managing learning materials.
    
    Ensures materials are uniquely identified and can be referenced
    for provenance tracking.
    """
    
    def __init__(self):
        """Initialize an empty material registry."""
        self._materials: dict[str, Material] = {}
    
    def add_material(self, material: Material) -> None:
        """
        Add a material to the registry.
        
        Args:
            material: The material to add
            
        Raises:
            ValueError: If a material with this ID already exists
        """
        if material.id in self._materials:
            raise ValueError(f"Material with ID '{material.id}' already exists")
        self._materials[material.id] = material
    
    def get_material(self, material_id: str) -> Material:
        """
        Retrieve a material by ID.
        
        Args:
            material_id: The ID of the material to retrieve
            
        Returns:
            The requested material
            
        Raises:
            KeyError: If no material with this ID exists
        """
        if material_id not in self._materials:
            raise KeyError(f"Material with ID '{material_id}' not found")
        return self._materials[material_id]
    
    def has_material(self, material_id: str) -> bool:
        """
        Check if a material exists in the registry.
        
        Args:
            material_id: The ID to check
            
        Returns:
            True if the material exists, False otherwise
        """
        return material_id in self._materials
    
    def get_all_materials(self) -> list[Material]:
        """
        Get all materials in the registry.
        
        Returns:
            List of all materials
        """
        return list(self._materials.values())
    
    def remove_material(self, material_id: str) -> None:
        """
        Remove a material from the registry.
        
        Args:
            material_id: The ID of the material to remove
            
        Raises:
            KeyError: If no material with this ID exists
        """
        if material_id not in self._materials:
            raise KeyError(f"Material with ID '{material_id}' not found")
        del self._materials[material_id]
