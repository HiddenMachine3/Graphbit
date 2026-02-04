"""
Phase 2 Demo: Knowledge Graph Reasoning Operations

Demonstrates the new graph reasoning capabilities added in Phase 2.
"""

from backend.app.domain import Graph, Node, Edge, EdgeType


def main():
    print("=" * 70)
    print("Phase 2: Knowledge Graph Reasoning Demo")
    print("=" * 70)
    
    # Create a knowledge graph representing Python learning path
    graph = Graph()
    
    # Add nodes
    concepts = [
        ("python_basics", "Python Basics"),
        ("variables", "Variables and Data Types"),
        ("control_flow", "Control Flow"),
        ("functions", "Functions"),
        ("data_structures", "Data Structures"),
        ("oop", "Object-Oriented Programming"),
        ("decorators", "Decorators"),
        ("generators", "Generators"),
        ("async", "Async/Await"),
    ]
    
    for node_id, topic_name in concepts:
        graph.add_node(Node(id=node_id, topic_name=topic_name))
    
    print(f"\n✓ Created graph with {len(concepts)} knowledge nodes")
    
    # Add prerequisite relationships
    prerequisites = [
        ("python_basics", "variables"),
        ("python_basics", "control_flow"),
        ("variables", "functions"),
        ("control_flow", "functions"),
        ("functions", "data_structures"),
        ("functions", "oop"),
        ("oop", "decorators"),
        ("functions", "generators"),
        ("generators", "async"),
    ]
    
    for from_id, to_id in prerequisites:
        graph.add_edge(Edge(
            from_node_id=from_id,
            to_node_id=to_id,
            weight=0.8,
            type=EdgeType.PREREQUISITE
        ))
    
    print(f"✓ Added {len(prerequisites)} prerequisite relationships")
    
    # Demo 1: Neighbor Queries
    print("\n" + "=" * 70)
    print("DEMO 1: Neighbor Queries")
    print("=" * 70)
    
    node_id = "functions"
    outgoing = graph.get_outgoing_neighbors(node_id)
    incoming = graph.get_incoming_neighbors(node_id)
    
    print(f"\n'{graph.nodes[node_id].topic_name}':")
    print(f"  Prerequisites (incoming): {[graph.nodes[n].topic_name for n in incoming]}")
    print(f"  Unlocks (outgoing): {[graph.nodes[n].topic_name for n in outgoing]}")
    
    # Filter by edge type
    prereqs = graph.get_neighbors_by_edge_type("python_basics", {EdgeType.PREREQUISITE})
    print(f"\n'Python Basics' prerequisites:")
    print(f"  → {[graph.nodes[n].topic_name for n in prereqs]}")
    
    # Demo 2: Path Existence
    print("\n" + "=" * 70)
    print("DEMO 2: Path Existence Checking")
    print("=" * 70)
    
    test_pairs = [
        ("python_basics", "async", 5),
        ("python_basics", "async", 3),
        ("variables", "decorators", 4),
    ]
    
    for from_id, to_id, max_hops in test_pairs:
        exists = graph.path_exists(from_id, to_id, max_hops)
        from_name = graph.nodes[from_id].topic_name
        to_name = graph.nodes[to_id].topic_name
        status = "✓ Connected" if exists else "✗ Not connected"
        print(f"\n{from_name} → {to_name} (max {max_hops} hops):")
        print(f"  {status}")
    
    # Demo 3: Shortest Path
    print("\n" + "=" * 70)
    print("DEMO 3: Finding Learning Paths")
    print("=" * 70)
    
    path_queries = [
        ("python_basics", "oop", 10),
        ("variables", "async", 10),
        ("python_basics", "async", 3),  # Too short
    ]
    
    for from_id, to_id, max_hops in path_queries:
        path = graph.shortest_path(from_id, to_id, max_hops)
        from_name = graph.nodes[from_id].topic_name
        to_name = graph.nodes[to_id].topic_name
        
        print(f"\n{from_name} → {to_name}:")
        if path:
            path_names = [graph.nodes[n].topic_name for n in path]
            print(f"  Path ({len(path)-1} hops): {' → '.join(path_names)}")
        else:
            print(f"  No path found within {max_hops} hops")
    
    # Demo 4: Valid Coverage Validation
    print("\n" + "=" * 70)
    print("DEMO 4: Question Coverage Validation")
    print("=" * 70)
    
    # Test different question coverage scenarios
    coverage_tests = [
        {
            "nodes": ["variables", "functions"],
            "max_hops": 2,
            "description": "Closely related topics"
        },
        {
            "nodes": ["variables", "functions", "data_structures"],
            "max_hops": 2,
            "description": "Sequential learning path"
        },
        {
            "nodes": ["python_basics", "async"],
            "max_hops": 3,
            "description": "Too far apart"
        },
        {
            "nodes": ["python_basics", "async"],
            "max_hops": 5,
            "description": "Distant but connected"
        },
    ]
    
    for test in coverage_tests:
        nodes = test["nodes"]
        max_hops = test["max_hops"]
        is_valid = graph.is_valid_coverage(nodes, max_hops, {EdgeType.PREREQUISITE})
        
        node_names = [graph.nodes[n].topic_name for n in nodes]
        status = "✓ Valid" if is_valid else "✗ Invalid"
        
        print(f"\n{test['description']}:")
        print(f"  Topics: {', '.join(node_names)}")
        print(f"  Max distance: {max_hops} hops")
        print(f"  {status} coverage")
    
    # Demo 5: Advanced Graph Analysis
    print("\n" + "=" * 70)
    print("DEMO 5: Learning Path Analysis")
    print("=" * 70)
    
    # Find all topics reachable from basics
    print("\nStarting from 'Python Basics', you can learn:")
    reachable_1_hop = [n for n in graph.get_outgoing_neighbors("python_basics")]
    print(f"  1 hop away: {[graph.nodes[n].topic_name for n in reachable_1_hop]}")
    
    # Find what requires functions as prerequisite
    unlocked_by_functions = graph.get_outgoing_neighbors("functions")
    print(f"\nMastering 'Functions' unlocks:")
    for node_id in unlocked_by_functions:
        print(f"  → {graph.nodes[node_id].topic_name}")
    
    # Check if advanced topics are connected
    print("\nAdvanced topics connectivity:")
    advanced = ["decorators", "generators", "async"]
    for i, node_a in enumerate(advanced):
        for node_b in advanced[i+1:]:
            connected = (graph.path_exists(node_a, node_b, max_hops=3) or 
                        graph.path_exists(node_b, node_a, max_hops=3))
            status = "✓" if connected else "✗"
            name_a = graph.nodes[node_a].topic_name
            name_b = graph.nodes[node_b].topic_name
            print(f"  {status} {name_a} ↔ {name_b}")
    
    print("\n" + "=" * 70)
    print("✓ Phase 2 Demo completed successfully!")
    print("=" * 70)


if __name__ == "__main__":
    main()
