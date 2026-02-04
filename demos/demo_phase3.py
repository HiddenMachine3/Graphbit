"""
Phase 3 Demonstration: User Knowledge State & Forgetting Model

This demonstrates tracking individual user knowledge states over time with forgetting curves.
"""

from datetime import datetime, timedelta
from backend.app.domain import Node, UserNodeState

print("=" * 70)
print("PHASE 3: User Knowledge State & Forgetting Model")
print("=" * 70)
print()

# Create some nodes for our demonstration
nodes = {
    "python_basics": Node(
        id="python_basics",
        topic_name="Python Basics",
        importance=8.0,
    ),
    "data_structures": Node(
        id="data_structures",
        topic_name="Data Structures",
        importance=9.0,
    ),
    "algorithms": Node(
        id="algorithms",
        topic_name="Algorithms",
        importance=10.0,
    ),
}

print("Created 3 learning nodes:")
for node_id, node in nodes.items():
    print(f"  • {node.topic_name} (importance: {node.importance})")
print()

# Scenario 1: Fresh learner starts studying Python basics
print("-" * 70)
print("SCENARIO 1: Fresh Learner - Initial State")
print("-" * 70)

user1_python = UserNodeState(
    user_id="alice",
    node_id="python_basics",
)

now = datetime.now()
initial_weakness = user1_python.weakness_score(now, importance=nodes["python_basics"].importance)
initial_forgetting = user1_python.forgetting_score(now)

print(f"User: alice")
print(f"Topic: Python Basics")
print(f"Initial PKR: {user1_python.proven_knowledge_rating:.2f}")
print(f"Initial stability: {user1_python.stability:.2f}")
print(f"Initial weakness score: {initial_weakness:.2f}")
print(f"Initial forgetting score: {initial_forgetting:.2f} (never reviewed)")
print()

# Scenario 2: Learning progression through multiple successful reviews
print("-" * 70)
print("SCENARIO 2: Learning Progression")
print("-" * 70)

print("Alice studies Python basics over 5 days...")
print()

for day in range(5):
    review_time = now + timedelta(days=day)
    user1_python.record_success(review_time)
    
    weakness = user1_python.weakness_score(review_time, importance=nodes["python_basics"].importance)
    forgetting = user1_python.forgetting_score(review_time)
    
    print(f"Day {day + 1}: ✓ Success")
    print(f"  PKR: {user1_python.proven_knowledge_rating:.3f}")
    print(f"  Stability: {user1_python.stability:.2f}")
    print(f"  Weakness: {weakness:.3f}")
    print(f"  Forgetting: {forgetting:.3f}")
    print()

# Scenario 3: Forgetting over time
print("-" * 70)
print("SCENARIO 3: Forgetting Curve")
print("-" * 70)

print("Alice stops reviewing for 30 days...")
print()

last_review = user1_python.last_reviewed_at
pkr_after_learning = user1_python.proven_knowledge_rating

for days_elapsed in [1, 3, 7, 14, 30]:
    check_time = last_review + timedelta(days=days_elapsed)
    forgetting = user1_python.forgetting_score(check_time)
    weakness = user1_python.weakness_score(check_time, importance=nodes["python_basics"].importance)
    
    print(f"After {days_elapsed} days:")
    print(f"  PKR: {pkr_after_learning:.3f} (unchanged)")
    print(f"  Forgetting: {forgetting:.3f}")
    print(f"  Weakness: {weakness:.3f}")
    print()

# Scenario 4: Relearning after forgetting
print("-" * 70)
print("SCENARIO 4: Relearning Cycle")
print("-" * 70)

relearn_time = last_review + timedelta(days=30)
print("After 30 days, Alice reviews again...")
print()

# First attempt fails (rusty!)
user1_python.record_failure(relearn_time)
print(f"Review 1: ✗ Failure")
print(f"  PKR: {user1_python.proven_knowledge_rating:.3f} (decreased)")
print(f"  Stability: {user1_python.stability:.2f} (decreased)")
print()

# Next two attempts succeed
user1_python.record_success(relearn_time + timedelta(days=1))
print(f"Review 2: ✓ Success")
print(f"  PKR: {user1_python.proven_knowledge_rating:.3f}")
print(f"  Stability: {user1_python.stability:.2f}")
print()

user1_python.record_success(relearn_time + timedelta(days=2))
print(f"Review 3: ✓ Success")
print(f"  PKR: {user1_python.proven_knowledge_rating:.3f}")
print(f"  Stability: {user1_python.stability:.2f}")
print()

# Scenario 5: Multiple users, different mastery levels
print("-" * 70)
print("SCENARIO 5: Comparing Multiple Users")
print("-" * 70)

# Alice (experienced, studied recently)
alice_algorithms = UserNodeState(
    user_id="alice",
    node_id="algorithms",
    proven_knowledge_rating=0.8,
    stability=4.0,
    last_reviewed_at=now - timedelta(days=2),
)

# Bob (beginner, just started)
bob_algorithms = UserNodeState(
    user_id="bob",
    node_id="algorithms",
    proven_knowledge_rating=0.2,
    stability=1.0,
    last_reviewed_at=now - timedelta(days=1),
)

# Carol (intermediate, but hasn't reviewed in a while)
carol_algorithms = UserNodeState(
    user_id="carol",
    node_id="algorithms",
    proven_knowledge_rating=0.6,
    stability=2.5,
    last_reviewed_at=now - timedelta(days=20),
)

print(f"Topic: {nodes['algorithms'].topic_name} (importance: {nodes['algorithms'].importance})")
print()

check_time = now
importance = nodes["algorithms"].importance

users = [
    ("Alice", alice_algorithms),
    ("Bob", bob_algorithms),
    ("Carol", carol_algorithms),
]

for name, state in users:
    weakness = state.weakness_score(check_time, importance=importance)
    forgetting = state.forgetting_score(check_time)
    days_since = (check_time - state.last_reviewed_at).days if state.last_reviewed_at else None
    
    print(f"{name}:")
    print(f"  PKR: {state.proven_knowledge_rating:.2f}")
    print(f"  Stability: {state.stability:.2f}")
    print(f"  Last reviewed: {days_since} days ago" if days_since else "  Last reviewed: Never")
    print(f"  Forgetting: {forgetting:.3f}")
    print(f"  Weakness: {weakness:.3f}")
    print()

# Scenario 6: Weakness-based prioritization
print("-" * 70)
print("SCENARIO 6: Weakness-Based Study Prioritization")
print("-" * 70)

print("Determining which topic Alice should review next...")
print()

# Create states for all topics for Alice
alice_states = {
    "python_basics": user1_python,  # Well learned recently
    "data_structures": UserNodeState(
        user_id="alice",
        node_id="data_structures",
        proven_knowledge_rating=0.5,
        stability=2.0,
        last_reviewed_at=now - timedelta(days=10),
    ),
    "algorithms": alice_algorithms,  # Well learned, recent
}

# Calculate weakness scores
weakness_scores = []
for node_id, state in alice_states.items():
    node = nodes[node_id]
    weakness = state.weakness_score(now, importance=node.importance)
    weakness_scores.append((node.topic_name, weakness, state))

# Sort by weakness (highest first)
weakness_scores.sort(key=lambda x: x[1], reverse=True)

print("Topics ranked by weakness (should review first):")
print()

for rank, (topic_name, weakness, state) in enumerate(weakness_scores, 1):
    days_since = (now - state.last_reviewed_at).days if state.last_reviewed_at else "Never"
    print(f"{rank}. {topic_name}")
    print(f"   Weakness: {weakness:.3f}")
    print(f"   PKR: {state.proven_knowledge_rating:.2f}")
    print(f"   Last review: {days_since} days ago" if isinstance(days_since, int) else f"   Last review: {days_since}")
    print()

print("=" * 70)
print("Phase 3 Demonstration Complete!")
print()
print("Key Features Demonstrated:")
print("  • Initial knowledge state tracking")
print("  • Learning progression with successful reviews")
print("  • Exponential forgetting curves over time")
print("  • Relearning after forgetting periods")
print("  • Multi-user knowledge comparison")
print("  • Weakness-based study prioritization")
print("=" * 70)
