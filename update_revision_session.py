#!/usr/bin/env python3
"""
Update RevisionSession constructors to add project_id parameter.
"""

import re
from pathlib import Path

def update_revision_session(file_path: Path):
    """Update RevisionSession constructors in test_revision_session.py"""
    content = file_path.read_text(encoding='utf-8')
    original = content
    
    # Pattern: RevisionSession(user_id="...", graph=..., question_bank=..., user_node_states=..., session_config=...)
    # We need to add project_id="test_project_1" after user_id
    
    # First handle the multi-line version
    pattern = r'(RevisionSession\(\s*user_id=(["\'][^"\']+["\'])\s*,)'
    replacement = r'\1\n            project_id="test_project_1",'
    
    new_content = re.sub(pattern, replacement, content)
    
    # Also handle single-line version: RevisionSession("user1", graph, bank, user_states, config)
    pattern2 = r'RevisionSession\((["\'][^"\']+["\'])\s*,\s*(\w+)\s*,\s*(\w+)\s*,\s*(\w+)\s*,\s*(\w+)\)'
    replacement2 = r'RevisionSession(\1, "test_project_1", \2, \3, \4, \5)'
    
    new_content = re.sub(pattern2, replacement2, new_content)
    
    if new_content != original:
        file_path.write_text(new_content, encoding='utf-8')
        print(f"✓ Updated {file_path.name}")
        return True
    else:
        print(f"  No changes needed for {file_path.name}")
        return False

def main():
    """Main entry point."""
    file_path = Path(__file__).parent / "tests" / "test_revision_session.py"
    
    if file_path.exists():
        update_revision_session(file_path)
    else:
        print(f"✗ File not found: {file_path}")

if __name__ == "__main__":
    main()
