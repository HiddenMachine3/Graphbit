"""Pytest configuration to handle import paths."""

import sys
from pathlib import Path
import pytest
from datetime import datetime

# Add Backend directory to Python path
backend_dir = Path(__file__).parent.parent / "Backend"
sys.path.insert(0, str(backend_dir))

# Create 'backend' namespace module that points to 'app'
class BackendNamespace:
    app = None

sys.modules['backend'] = sys.modules['sys']

# Import app module first
import app as app_module
sys.modules['backend.app'] = app_module

# Also make submodules accessible
from app import domain
sys.modules['backend.app.domain'] = domain


# ============================================================
# TEST FIXTURES
# ============================================================


@pytest.fixture
def test_project_id():
    """Default test project ID."""
    return "test_project_1"


@pytest.fixture
def test_project():
    """Create a test project."""
    from backend.app.domain import Project, ProjectVisibility
    return Project(
        id="test_project_1",
        name="Test Project",
        description="A test project for unit tests",
        owner_id="test_user_1",
        visibility=ProjectVisibility.PRIVATE,
        created_at=datetime(2024, 1, 1),
        updated_at=datetime(2024, 1, 1),
    )
