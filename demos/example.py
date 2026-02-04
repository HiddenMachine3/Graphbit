"""
Example usage of the core domain models.
Demonstrates creating a simple knowledge graph with nodes, edges, and questions.
"""

from datetime import datetime

from models import (
    Community,
    Edge,
    EdgeType,
    Graph,
    KnowledgeType,
    Node,
    Question,
    QuestionMetadata,
    QuestionType,
    User,
)


def main():
    print("=" * 70)
    print("Graph-Based Active Recall System - Domain Models Demo")
    print("=" * 70)
    
    # Create a knowledge graph
    graph = Graph()
    print("\n✓ Created empty knowledge graph")
    
    # Add nodes representing Python concepts
    nodes = [
        Node(
            id="python_basics",
            topic_name="Python Basics",
            proven_knowledge_rating=0.8,
            importance=10.0,
            relevance=9.0,
        ),
        Node(
            id="variables",
            topic_name="Variables and Data Types",
            proven_knowledge_rating=0.9,
            importance=8.0,
            relevance=8.0,
        ),
        Node(
            id="functions",
            topic_name="Functions",
            proven_knowledge_rating=0.7,
            importance=9.0,
            relevance=9.0,
        ),
        Node(
            id="classes",
            topic_name="Classes and OOP",
            proven_knowledge_rating=0.5,
            importance=7.0,
            relevance=6.0,
        ),
    ]
    
    for node in nodes:
        graph.add_node(node)
    
    print(f"✓ Added {len(nodes)} knowledge nodes to the graph")
    
    # Add edges showing relationships
    edges = [
        Edge(
            from_node_id="python_basics",
            to_node_id="variables",
            weight=0.9,
            type=EdgeType.SUBCONCEPT_OF,
        ),
        Edge(
            from_node_id="python_basics",
            to_node_id="functions",
            weight=0.8,
            type=EdgeType.SUBCONCEPT_OF,
        ),
        Edge(
            from_node_id="variables",
            to_node_id="functions",
            weight=0.7,
            type=EdgeType.PREREQUISITE,
        ),
        Edge(
            from_node_id="functions",
            to_node_id="classes",
            weight=0.9,
            type=EdgeType.PREREQUISITE,
        ),
    ]
    
    for edge in edges:
        graph.add_edge(edge)
    
    print(f"✓ Added {len(edges)} edges showing concept relationships")
    
    # Create a question
    question = Question(
        id="q1",
        text="What keyword is used to define a function in Python?",
        answer="def",
        question_type=QuestionType.FLASHCARD,
        knowledge_type=KnowledgeType.FACT,
        covered_node_ids=["functions"],
        metadata=QuestionMetadata(
            created_by="instructor_1",
            created_at=datetime.now(),
            importance=8.0,
        ),
    )
    
    print(f"\n✓ Created question: '{question.text}'")
    
    # Simulate answering the question
    question.record_hit()
    question.record_hit()
    question.record_miss()
    
    print(f"  - Hits: {question.metadata.hits}, Misses: {question.metadata.misses}")
    print(f"  - Success rate: {question.success_rate:.1%}")
    
    # Create a user
    user = User(
        id="user_123",
        name="Alice Johnson",
        email="alice@example.com",
    )
    
    print(f"\n✓ Created user: {user.name} ({user.email})")
    
    # Create a community
    community = Community(
        id="comm_python",
        name="Python Masters",
        description="Community for advanced Python learners",
    )
    
    # Set custom importance for some nodes
    community.set_node_importance("classes", 15.0)
    community.set_node_importance("functions", 12.0)
    
    print(f"\n✓ Created community: {community.name}")
    print(f"  - Importance overrides: {len(community.node_importance_overrides)} nodes")
    
    # User joins community
    user.join_community(community.id)
    print(f"  - {user.name} joined the community")
    
    # Display graph statistics
    print("\n" + "=" * 70)
    print("Graph Statistics")
    print("=" * 70)
    print(f"Total nodes: {len(graph.nodes)}")
    print(f"Total edges: {len(graph.edges)}")
    
    print("\nNode Details:")
    for node_id, node in graph.nodes.items():
        print(f"  • {node.topic_name}")
        print(f"    - Proven mastery: {node.proven_knowledge_rating:.1%}")
        print(f"    - Importance: {node.importance}")
        
        # Check for community override
        if node_id in community.node_importance_overrides:
            override = community.node_importance_overrides[node_id]
            print(f"    - Community override: {override} ⭐")
    
    print("\nRelationships:")
    for edge in graph.edges:
        from_node = graph.nodes[edge.from_node_id]
        to_node = graph.nodes[edge.to_node_id]
        print(
            f"  • {from_node.topic_name} -> {to_node.topic_name} "
            f"({edge.type.value}, weight: {edge.weight})"
        )
    
    # Demonstrate safe updates
    print("\n" + "=" * 70)
    print("Demonstrating Safe Updates")
    print("=" * 70)
    
    node = graph.nodes["classes"]
    original_rating = node.proven_knowledge_rating
    print(f"\nCurrent mastery of '{node.topic_name}': {original_rating:.1%}")
    
    # Simulate learning progress
    node.update_proven_rating(0.75)
    print(f"After learning session: {node.proven_knowledge_rating:.1%}")
    
    node.increment_view_frequency()
    node.increment_view_frequency()
    print(f"View frequency: {node.view_frequency}")
    
    print("\n" + "=" * 70)
    print("✓ Demo completed successfully!")
    print("=" * 70)


if __name__ == "__main__":
    main()
