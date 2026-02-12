"""Database models package."""
from sqlalchemy import Column, Integer, String, Boolean, TIMESTAMP, Text, Float, JSON
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.sql import func
import json

from app.db.types import VectorType, SearchVectorType


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


class AppUser(Base):
    """Application user model for local authentication."""
    __tablename__ = "app_users"

    id = Column(String, primary_key=True, nullable=False)
    username = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)
    avatar_url = Column(String, nullable=True)
    active_community_id = Column(String, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), onupdate=func.now())


class User(Base):
    """User model for authentication.
    
    Stores user account information including:
    - Email (unique identifier for login)
    - Hashed password (never store plain passwords!)
    - Account status flags (active, superuser, verified)
    - Timestamps for audit trail
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), onupdate=func.now())


class Question(Base):
    """Question model for revision sessions.
    
    Stores questions for active recall practice:
    - Text and answer content
    - Question type (OPEN, MCQ, etc.)
    - Knowledge metadata and coverage
    - Difficulty level and tags
    """
    __tablename__ = "questions"

    id = Column(String, primary_key=True, nullable=False)
    project_id = Column(String, nullable=False)
    created_by = Column(String, nullable=False)
    text = Column(String, nullable=False)
    answer = Column(Text, nullable=False)
    options = Column(JSON, nullable=True)  # MCQ options when applicable
    option_explanations = Column(JSON, nullable=True)  # Optional MCQ option explanations
    question_type = Column(String, nullable=False)  # OPEN, MCQ, etc.
    knowledge_type = Column(String, nullable=False)  # CONCEPT, FACT, etc.
    covered_node_ids = Column(JSON, nullable=False)  # List of node IDs
    difficulty = Column(Integer, default=3, nullable=False)
    tags = Column(JSON, nullable=False, default=lambda: [])  # List of tags
    question_metadata = Column(JSON, nullable=False)  # created_by, created_at, importance, hits, misses
    last_attempted_at = Column(TIMESTAMP(timezone=True), nullable=True)
    source_material_ids = Column(JSON, nullable=False, default=lambda: [])
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), onupdate=func.now())


class RevisionSession(Base):
    """Revision session model for tracking user practice sessions.
    
    Stores session information:
    - Session metadata (start time, questions answered)
    - MCQ options for questions if needed
    """
    __tablename__ = "revision_sessions"

    id = Column(String, primary_key=True, nullable=False)
    user_id = Column(String, nullable=True)  # Optional user ID
    project_id = Column(String, nullable=True)
    max_questions = Column(Integer, default=10, nullable=False)
    questions_answered = Column(Integer, default=0, nullable=False)
    question_index = Column(Integer, default=0, nullable=False)
    current_question_id = Column(String, nullable=True)
    started_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    ended_at = Column(TIMESTAMP(timezone=True), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), onupdate=func.now())


class Project(Base):
    """Project model for knowledge graphs and learning content."""
    __tablename__ = "projects"

    id = Column(String, primary_key=True, nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=False, default="")
    owner_id = Column(String, nullable=False)
    created_by = Column(String, nullable=False)
    visibility = Column(String, nullable=False, default="private")
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), onupdate=func.now())


class Community(Base):
    """Community model for grouping projects and overrides."""
    __tablename__ = "communities"

    id = Column(String, primary_key=True, nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=False, default="")
    created_by = Column(String, nullable=False)
    project_ids = Column(JSON, nullable=False, default=lambda: [])
    member_ids = Column(JSON, nullable=False, default=lambda: [])
    node_importance_overrides = Column(JSON, nullable=False, default=lambda: {})
    question_importance_overrides = Column(JSON, nullable=False, default=lambda: {})
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), onupdate=func.now())


class Node(Base):
    """Knowledge graph node model."""
    __tablename__ = "nodes"

    id = Column(String, primary_key=True, nullable=False)
    project_id = Column(String, nullable=False)
    created_by = Column(String, nullable=False)
    topic_name = Column(String, nullable=False)
    proven_knowledge_rating = Column(Float, nullable=False, default=0.0)
    user_estimated_knowledge_rating = Column(Float, nullable=False, default=0.0)
    importance = Column(Float, nullable=False, default=0.5)
    relevance = Column(Float, nullable=False, default=0.5)
    view_frequency = Column(Integer, nullable=False, default=0)
    source_material_ids = Column(JSON, nullable=False, default=lambda: [])
    embedding = Column(VectorType(768), nullable=True)
    search_vector = Column(SearchVectorType(), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), onupdate=func.now())


class Edge(Base):
    """Knowledge graph edge model."""
    __tablename__ = "edges"

    id = Column(String, primary_key=True, nullable=False)
    project_id = Column(String, nullable=False)
    source = Column(String, nullable=False)
    target = Column(String, nullable=False)
    type = Column(String, nullable=False)
    weight = Column(Float, nullable=False, default=1.0)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), onupdate=func.now())


class Material(Base):
    """Study material model."""
    __tablename__ = "materials"

    id = Column(String, primary_key=True, nullable=False)
    project_id = Column(String, nullable=False)
    created_by = Column(String, nullable=False)
    title = Column(String, nullable=False)
    source_url = Column(Text, nullable=True)
    content_text = Column(Text, nullable=False)
    summary = Column(Text, nullable=True)
    embedding = Column(VectorType(768), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), onupdate=func.now())


class MaterialNodeSuggestion(Base):
    """Material to node suggestion model."""
    __tablename__ = "material_node_suggestions"

    id = Column(String, primary_key=True, nullable=False)
    material_id = Column(String, nullable=False)
    node_id = Column(String, nullable=True)
    suggested_title = Column(String, nullable=True)
    suggested_description = Column(Text, nullable=True)
    confidence = Column(Float, nullable=False, default=0.0)
    suggestion_type = Column(String, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
