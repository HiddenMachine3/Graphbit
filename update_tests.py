#!/usr/bin/env python3
"""
Bulk update script to add project_id parameters to test files.
"""

import re
from pathlib import Path

def update_file(file_path: Path):
    """Update a single test file."""
    content = file_path.read_text(encoding='utf-8')
    original = content
    
    # Count updates
    updates = []
    
    # Pattern 1: Graph() -> Graph(project_id="test_project_1")
    pattern = r'Graph\(\)'
    replacement = r'Graph(project_id="test_project_1")'
    if re.search(pattern, content):
        content = re.sub(pattern, replacement, content)
        updates.append(f"Updated Graph()")
    
    # Pattern 2: Node(id="...", topic_name="...") -> add project_id
    # Match Node(...) but not those that already have project_id
    pattern = r'Node\(id=(["\'][^"\']+["\'])((?:,\s*[^)]*)?)\)'
    def node_replacement(match):
        node_id = match.group(1)
        rest = match.group(2)
        if 'project_id=' in rest:
            return match.group(0)  # Already has project_id
        # Insert project_id after id
        return f'Node(id={node_id}, project_id="test_project_1"{rest})'
    
    new_content = re.sub(pattern, node_replacement, content)
    if new_content != content:
        updates.append(f"Updated Node constructors")
        content = new_content
    
    # Pattern 3: Edge(from_node_id="...", to_node_id="...", ...) -> add project_id  
    pattern = r'Edge\(\s*from_node_id=(["\'][^"\']+["\'])\s*,\s*to_node_id=(["\'][^"\']+["\'])((?:,\s*[^)]*)?)\)'
    def edge_replacement(match):
        from_id = match.group(1)
        to_id = match.group(2)
        rest = match.group(3)
        if 'project_id=' in rest:
            return match.group(0)  # Already has project_id
        # Insert project_id after to_node_id
        return f'Edge(from_node_id={from_id}, to_node_id={to_id}, project_id="test_project_1"{rest})'
    
    new_content = re.sub(pattern, edge_replacement, content)
    if new_content != content:
        updates.append(f"Updated Edge constructors")
        content = new_content
    
    # Pattern 4: UserNodeState(user_id="...", node_id="...", ...) -> add project_id
    pattern = r'UserNodeState\(\s*user_id=(["\'][^"\']+["\'])\s*,\s*node_id=(["\'][^"\']+["\'])((?:,\s*[^)]*)?)\)'
    def userstate_replacement(match):
        user_id = match.group(1)
        node_id = match.group(2)
        rest = match.group(3)
        if 'project_id=' in rest:
            return match.group(0)  # Already has project_id
        # Insert project_id after node_id
        return f'UserNodeState(user_id={user_id}, node_id={node_id}, project_id="test_project_1"{rest})'
    
    new_content = re.sub(pattern, userstate_replacement, content)
    if new_content != content:
        updates.append(f"Updated UserNodeState constructors")
        content = new_content
    
    # Pattern 5: Question(...) without project_id -> add project_id
    pattern = r'Question\(\s*id=(["\'][^"\']+["\'])((?:,\s*[^)]*)?)\)'
    def question_replacement(match):
        q_id = match.group(1)
        rest = match.group(2)
        if 'project_id=' in rest:
            return match.group(0)  # Already has project_id
        # Insert project_id after id
        return f'Question(id={q_id}, project_id="test_project_1"{rest})'
    
    new_content = re.sub(pattern, question_replacement, content)
    if new_content != content:
        updates.append(f"Updated Question constructors")
        content = new_content
    
    # Pattern 6: Material(...) without project_id -> add project_id
    pattern = r'Material\(\s*id=(["\'][^"\']+["\'])((?:,\s*[^)]*)?)\)'
    def material_replacement(match):
        m_id = match.group(1)
        rest = match.group(2)
        if 'project_id=' in rest:
            return match.group(0)  # Already has project_id
        # Insert project_id after id
        return f'Material(id={m_id}, project_id="test_project_1"{rest})'
    
    new_content = re.sub(pattern, material_replacement, content)
    if new_content != content:
        updates.append(f"Updated Material constructors")
        content = new_content
    
    # Pattern 7: ContentSession(...) without project_id -> add project_id
    pattern = r'ContentSession\(\s*session_id=(["\'][^"\']+["\'])\s*,\s*material_id=(["\'][^"\']+["\'])\s*,\s*user_id=(["\'][^"\']+["\'])((?:,\s*[^)]*)?)\)'
    def session_replacement(match):
        session_id = match.group(1)
        material_id = match.group(2)
        user_id = match.group(3)
        rest = match.group(4)
        if 'project_id=' in rest:
            return match.group(0)  # Already has project_id
        # Insert project_id after user_id
        return f'ContentSession(session_id={session_id}, material_id={material_id}, user_id={user_id}, project_id="test_project_1"{rest})'
    
    new_content = re.sub(pattern, session_replacement, content)
    if new_content != content:
        updates.append(f"Updated ContentSession constructors")
        content = new_content
    
    # Pattern 8: Community(...) without project_ids -> add project_ids
    # This is more complex because we need to add project_ids as a set
    pattern = r'Community\(\s*id=(["\'][^"\']+["\'])\s*,\s*name=(["\'][^"\']+["\'])((?:,\s*[^)]*)?)\)'
    def community_replacement(match):
        comm_id = match.group(1)
        name = match.group(2)
        rest = match.group(3)
        if 'project_ids=' in rest:
            return match.group(0)  # Already has project_ids
        # Insert project_ids after name
        return f'Community(id={comm_id}, name={name}, project_ids={{\"test_project_1\"}}{rest})'
    
    new_content = re.sub(pattern, community_replacement, content)
    if new_content != content:
        updates.append(f"Updated Community constructors")
        content = new_content
    
    # Pattern 9: community.set_node_importance("node1", importance) -> 
    # community.set_node_importance("test_project_1", "node1", importance)
    pattern = r'(\w+)\.set_node_importance\((["\'][^"\']+["\'])\s*,\s*(\d+(?:\.\d+)?)\)'
    def set_importance_replacement(match):
        obj = match.group(1)
        node_id = match.group(2)
        importance = match.group(3)
        # Check if it's already updated (has 3 parameters with "test_project_1")
        if node_id == '"test_project_1"' or node_id == "'test_project_1'":
            return match.group(0)
        return f'{obj}.set_node_importance("test_project_1", {node_id}, {importance})'
    
    new_content = re.sub(pattern, set_importance_replacement, content)
    if new_content != content:
        updates.append(f"Updated set_node_importance calls")
        content = new_content
    
    # Pattern 10: community.remove_node_importance_override("node1") -> 
    # community.remove_node_importance_override("test_project_1", "node1")
    pattern = r'(\w+)\.remove_node_importance_override\((["\'][^"\']+["\'])\)'
    def remove_importance_replacement(match):
        obj = match.group(1)
        node_id = match.group(2)
        # Check if it's already updated
        if node_id == '"test_project_1"' or node_id == "'test_project_1'":
            return match.group(0)
        return f'{obj}.remove_node_importance_override("test_project_1", {node_id})'
    
    new_content = re.sub(pattern, remove_importance_replacement, content)
    if new_content != content:
        updates.append(f"Updated remove_node_importance_override calls")
        content = new_content
    
    # Only write if content changed
    if content != original:
        file_path.write_text(content, encoding='utf-8')
        print(f"✓ Updated {file_path.name}: {', '.join(updates)}")
        return True
    else:
        print(f"  No changes needed for {file_path.name}")
        return False

def main():
    """Main entry point."""
    tests_dir = Path(__file__).parent / "tests"
    test_files = [
        "test_models.py",
        "test_graph_reasoning.py",
        "test_ingestion.py",
        "test_question_bank.py",
        "test_ranking.py",
        "test_user_knowledge.py",
        "test_interjection.py",
        "test_revision_session.py",
        "test_community_features.py",
        "test_weak_node_clustering.py",
    ]
    
    updated_count = 0
    for filename in test_files:
        file_path = tests_dir / filename
        if file_path.exists():
            if update_file(file_path):
                updated_count += 1
        else:
            print(f"✗ File not found: {filename}")
    
    print(f"\n{'='*60}")
    print(f"Updated {updated_count} out of {len(test_files)} files")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
