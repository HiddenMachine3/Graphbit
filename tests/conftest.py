"""Pytest configuration to handle import paths."""

import sys
from pathlib import Path

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
