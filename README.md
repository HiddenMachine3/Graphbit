We are building a graph-based active recall and revision system.

Core idea:
- Knowledge is modeled as a graph of nodes (concepts, facts, skills).
- Users have personalized mastery over nodes.
- Questions test one or more related nodes.
- The system later decides what to ask next based on forgetting, importance, and graph structure.
- Communities can define their own graphs, importance overrides, and question sets.

This project is built using test-driven development.
Each phase must be correct, validated, and independently testable.

Current phase: Phase 1 – Core Domain Models.
Only define domain entities, validation rules, and safe update logic.
No algorithms, persistence, APIs, or UI should be implemented yet.

---

## Phase 1: Core Domain Models ✅

**Status**: Complete

### Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run tests:
```bash
pytest test_models.py -v
```

### Domain Models Implemented

#### 1. **Node**
Represents a single unit of knowledge (concept, fact, skill).

**Fields:**
- `id`: Unique identifier (non-empty string)
- `topic_name`: Name of the knowledge node
- `proven_knowledge_rating`: System-measured mastery (0.0 to 1.0)
- `user_estimated_knowledge_rating`: User's self-assessment (0.0 to 1.0)
- `importance`: Importance score (≥ 0)
- `relevance`: Relevance score (≥ 0)
- `view_frequency`: Number of times viewed (≥ 0)

**Methods:**
- `update_proven_rating(new_rating)`: Safely update proven rating with validation
- `update_user_estimated_rating(new_rating)`: Safely update user rating with validation
- `increment_view_frequency()`: Increment view counter

#### 2. **Edge**
Represents a directed relationship between two knowledge nodes.

**Fields:**
- `from_node_id`: Source node ID
- `to_node_id`: Target node ID
- `weight`: Relationship strength (0.0 to 1.0)
- `type`: EdgeType enum (PREREQUISITE, DEPENDS_ON, APPLIED_WITH, SUBCONCEPT_OF)

**Validation:**
- Source and target nodes must be different
- Weight must be within [0, 1]

#### 3. **Graph**
Represents a knowledge graph containing nodes and their relationships.

**Fields:**
- `nodes`: Dictionary mapping node IDs to Node objects
- `edges`: List of Edge objects

**Methods:**
- `add_node(node)`: Add a node (prevents duplicates)
- `remove_node(node_id)`: Remove node and all connected edges
- `add_edge(edge)`: Add edge (validates node existence)
- `remove_edge(from_id, to_id)`: Remove specific edge

#### 4. **Question**
Represents an active recall question.

**Fields:**
- `id`: Unique identifier
- `text`: Question text
- `answer`: Correct answer
- `question_type`: QuestionType enum (FLASHCARD, CLOZE, MCQ, OPEN)
- `knowledge_type`: KnowledgeType enum (FACT, CONCEPT, PROCEDURE)
- `covered_node_ids`: List of node IDs tested by this question (≥ 1)
- `metadata`: QuestionMetadata object

**QuestionMetadata:**
- `created_by`: Creator ID
- `created_at`: Creation timestamp
- `importance`: Question importance (≥ 0)
- `hits`: Correct answer count (≥ 0)
- `misses`: Incorrect answer count (≥ 0)

**Methods:**
- `record_hit()`: Increment correct answer counter
- `record_miss()`: Increment incorrect answer counter
- `success_rate`: Property that calculates hit rate (returns None if no attempts)

#### 5. **User**
Represents a learner in the system.

**Fields:**
- `id`: Unique identifier
- `name`: User's name
- `email`: Email address (validated)
- `joined_community_ids`: Set of community IDs

**Methods:**
- `join_community(community_id)`: Add community membership
- `leave_community(community_id)`: Remove community membership

#### 6. **Community**
Represents a shared learning group.

**Fields:**
- `id`: Unique identifier
- `name`: Community name
- `description`: Description (optional)
- `node_importance_overrides`: Dictionary mapping node IDs to custom importance values

**Methods:**
- `set_node_importance(node_id, importance)`: Set/update importance override
- `remove_node_importance_override(node_id)`: Remove importance override

### Design Principles

✅ **Clean Domain-Driven Design**: Models represent pure domain entities with clear responsibilities

✅ **Validation**: Comprehensive validation using Pydantic v2 field validators and model validators

✅ **Immutability where appropriate**: Safe update methods with validation instead of direct field mutation for critical values

✅ **Type Safety**: Full type hints throughout

✅ **Framework-agnostic**: No dependencies on web frameworks, databases, or external services

✅ **Testability**: 100% test coverage with comprehensive test suite

### Test Coverage

Run tests with coverage report:
```bash
pytest test_models.py -v --cov=models --cov-report=term-missing
```

All business rules and constraints are validated:
- Rating bounds (0.0 to 1.0)
- Non-negative counters and scores
- Non-empty required fields
- Email format validation
- Graph referential integrity
- Edge self-reference prevention
- Community importance override validation

---

## Phase 2: Knowledge Graph Reasoning ✅

**Status**: Complete

### Overview

Phase 2 extends the Graph model with intelligent reasoning operations for structural queries. These methods enable path finding, connectivity analysis, and question coverage validation without modifying existing domain model contracts.

### Run Tests

```bash
pytest test_graph_reasoning.py -v
```

### New Graph Methods

#### 1. **Neighbor Queries**

**`get_outgoing_neighbors(node_id: str) -> list[str]`**
- Returns IDs of nodes directly reachable via outgoing edges
- Example: If A→B and A→C, calling on "A" returns ["B", "C"]

**`get_incoming_neighbors(node_id: str) -> list[str]`**
- Returns IDs of nodes that have edges pointing to this node
- Example: If A→C and B→C, calling on "C" returns ["A", "B"]

**`get_neighbors_by_edge_type(node_id: str, allowed_edge_types: set[EdgeType]) -> list[str]`**
- Returns outgoing neighbors filtered by edge type
- Example: Only follow PREREQUISITE edges

```python
# Get all prerequisites for a concept
prereqs = graph.get_neighbors_by_edge_type("advanced_python", {EdgeType.PREREQUISITE})
```

#### 2. **Path Existence**

**`path_exists(from_node_id: str, to_node_id: str, max_hops: int, allowed_edge_types: set[EdgeType] | None = None) -> bool`**
- Check if a path exists between two nodes within hop limit
- Uses BFS with bounded depth
- Returns True if any path exists, False otherwise

**Parameters:**
- `from_node_id`: Starting node
- `to_node_id`: Target node
- `max_hops`: Maximum number of hops (must be ≥ 1)
- `allowed_edge_types`: Optional edge type filter (None = all types)

**Example:**
```python
# Check if there's a path from basics to advanced within 3 hops
if graph.path_exists("python_basics", "design_patterns", max_hops=3):
    print("Topics are connected!")
```

#### 3. **Shortest Path**

**`shortest_path(from_node_id: str, to_node_id: str, max_hops: int, allowed_edge_types: set[EdgeType] | None = None) -> list[str] | None`**
- Find the shortest path between two nodes within hop limit
- Returns list of node IDs forming the path (including start and end)
- Returns None if no path exists within max_hops

**Example:**
```python
path = graph.shortest_path("A", "D", max_hops=5)
# Returns: ["A", "B", "C", "D"] or None
```

**Features:**
- Guarantees shortest path (BFS)
- Respects hop limits
- Handles cycles safely
- Edge type filtering

#### 4. **Valid Coverage Constraint**

**`is_valid_coverage(node_ids: list[str], max_hops: int, allowed_edge_types: set[EdgeType]) -> bool`**
- Validates that a set of nodes forms valid question coverage
- All pairs must be connected within max_hops (in either direction)
- Used to prevent bogus multi-topic questions

**Rules:**
- `node_ids` must contain at least 2 nodes
- Every pair must have a path within max_hops
- If any pair is disconnected, returns False

**Example:**
```python
# Validate that these topics are closely related
covered_nodes = ["variables", "functions", "loops"]
is_valid = graph.is_valid_coverage(
    covered_nodes, 
    max_hops=2, 
    allowed_edge_types={EdgeType.PREREQUISITE, EdgeType.SUBCONCEPT_OF}
)
```

### Usage Example

```python
from models import Graph, Node, Edge, EdgeType

# Build a knowledge graph
graph = Graph()

# Add nodes
graph.add_node(Node(id="python", topic_name="Python Basics"))
graph.add_node(Node(id="variables", topic_name="Variables"))
graph.add_node(Node(id="functions", topic_name="Functions"))
graph.add_node(Node(id="oop", topic_name="OOP"))

# Add edges
graph.add_edge(Edge(from_node_id="python", to_node_id="variables", weight=0.9, type=EdgeType.SUBCONCEPT_OF))
graph.add_edge(Edge(from_node_id="variables", to_node_id="functions", weight=0.8, type=EdgeType.PREREQUISITE))
graph.add_edge(Edge(from_node_id="functions", to_node_id="oop", weight=0.9, type=EdgeType.PREREQUISITE))

# Query neighbors
prereqs = graph.get_neighbors_by_edge_type("functions", {EdgeType.PREREQUISITE})
print(f"Prerequisites: {prereqs}")  # ["variables"]

# Find path
path = graph.shortest_path("python", "oop", max_hops=5)
print(f"Learning path: {' → '.join(path)}")  # python → variables → functions → oop

# Check connectivity
connected = graph.path_exists("python", "oop", max_hops=3)
print(f"Connected: {connected}")  # True

# Validate question coverage
valid = graph.is_valid_coverage(
    ["variables", "functions"], 
    max_hops=2, 
    allowed_edge_types={EdgeType.PREREQUISITE}
)
print(f"Valid coverage: {valid}")  # True
```

### Test Coverage (45 tests)

**Neighbor Queries (12 tests):**
- ✅ Outgoing neighbors (single/multiple/none)
- ✅ Incoming neighbors (single/multiple/none)
- ✅ Edge type filtering
- ✅ Error handling for nonexistent nodes

**Path Existence (13 tests):**
- ✅ Direct and multi-hop connections
- ✅ Max hop enforcement
- ✅ No connection cases
- ✅ Edge type filtering
- ✅ Same node paths
- ✅ Cycle handling
- ✅ Comprehensive error validation

**Shortest Path (10 tests):**
- ✅ Direct and multi-hop paths
- ✅ Chooses shortest when multiple paths exist
- ✅ Max hop enforcement
- ✅ Edge type filtering
- ✅ Returns None for no connection
- ✅ Error handling

**Valid Coverage (10 tests):**
- ✅ Two-node validation
- ✅ Bidirectional connections
- ✅ Multiple connected nodes
- ✅ Disconnected node detection
- ✅ Distance limit enforcement
- ✅ Edge type respect
- ✅ Partial connection detection
- ✅ Error handling

### Algorithm Details

**BFS (Breadth-First Search):**
- Used for `path_exists`, `shortest_path`
- Guarantees shortest path
- Time complexity: O(V + E) where V = nodes, E = edges
- Space complexity: O(V) for visited set

**Coverage Validation:**
- Checks all pairs: O(n²) where n = number of covered nodes
- Each pair check is O(V + E) using BFS
- Overall: O(n² × (V + E))

### Design Principles

✅ **Non-destructive**: Methods don't modify the graph

✅ **Backward compatible**: No changes to existing Graph API

✅ **Deterministic**: No randomness, reproducible results

✅ **Bounded**: All traversals respect hop limits to prevent infinite loops

✅ **Edge-type aware**: Support filtering by relationship type

✅ **Clear errors**: Meaningful exceptions for invalid inputs

✅ **Efficient**: BFS ensures optimal paths and performance

---

## Phase 3: User Knowledge State & Forgetting Model ✅

**Status**: Complete

Phase 3 introduces temporal knowledge tracking with exponential forgetting curves. It models how individual users master nodes over time, tracks review history, and calculates knowledge decay to prioritize reviews effectively.

### Running Phase 3

```bash
# Run Phase 3 tests
pytest test_user_knowledge.py -v

# Run demonstration
python demo_phase3.py

# Run all tests (146 total across all phases)
pytest -v
```

### New Model: UserNodeState

Tracks individual user mastery of specific knowledge nodes over time with forgetting curves.

**Fields:**
- `user_id`: User identifier (non-empty string)
- `node_id`: Node identifier (non-empty string)  
- `proven_knowledge_rating` (PKR): Current mastery level (0.0 to 1.0), default 0.0
- `review_count`: Number of reviews performed (≥ 0), default 0
- `last_reviewed_at`: Timestamp of last review (optional datetime), default None
- `stability`: Memory stability factor (> 0), default 1.0

**Methods:**

#### `record_success(reviewed_at: datetime) -> None`
Records a successful review attempt.

**Effects:**
- Increases PKR using diminishing returns: `PKR += SUCCESS_PKR_GAIN * (1 - PKR)`
- Increases stability: `stability *= SUCCESS_STABILITY_GAIN`  
- Increments review count
- Updates last reviewed timestamp
- PKR capped at 1.0, stability capped at MAX_STABILITY (10.0)

**Learning Rate Constants:**
- `SUCCESS_PKR_GAIN = 0.15`: Knowledge gain rate per success
- `SUCCESS_STABILITY_GAIN = 1.2`: Stability multiplier per success

#### `record_failure(reviewed_at: datetime) -> None`
Records a failed review attempt.

**Effects:**
- Decreases PKR: `PKR *= (1 - FAILURE_PKR_LOSS)`
- Decreases stability: `stability *= FAILURE_STABILITY_LOSS`
- Increments review count  
- Updates last reviewed timestamp
- PKR floored at 0.0, stability floored at MIN_STABILITY (0.1)

**Learning Rate Constants:**
- `FAILURE_PKR_LOSS = 0.20`: Knowledge loss rate per failure
- `FAILURE_STABILITY_LOSS = 0.8`: Stability multiplier per failure

#### `forgetting_score(current_time: datetime) -> float`
Calculates how much knowledge has been forgotten since last review.

**Formula:**
```
If never reviewed: return 1.0 (complete forgetting)
Otherwise: 1 - e^(-days_elapsed / stability)
```

**Returns:** Forgetting score from 0.0 (no forgetting) to 1.0 (complete forgetting)

**Characteristics:**
- Exponential decay curve
- Higher stability → slower forgetting
- Just reviewed → ~0.0
- Long time since review → approaches 1.0

#### `weakness_score(current_time: datetime, importance: float) -> float`
Calculates overall weakness score for prioritizing reviews.

**Formula:**
```
knowledge_gap = 1 - proven_knowledge_rating
forgetting = forgetting_score(current_time)
base_weakness = (knowledge_gap + forgetting) / 2
weakness = base_weakness * (1 + importance / 10)
```

**Parameters:**
- `current_time`: Time for forgetting calculation
- `importance`: Node importance (≥ 0)

**Returns:** Weakness score combining knowledge gaps, forgetting, and importance amplification

**Raises:** `ValueError` if importance is negative

### Phase 3 Demonstration Scenarios

The `demo_phase3.py` script demonstrates:

1. **Fresh Learner**: Initial state with zero knowledge
2. **Learning Progression**: PKR and stability increase over multiple successful reviews
3. **Forgetting Curve**: Knowledge decay over 30 days without review
4. **Relearning Cycle**: Failure after long break, then recovery through spaced practice
5. **Multi-User Comparison**: Different users at different mastery levels for same node
6. **Weakness-Based Prioritization**: Ranking topics by weakness score for optimal study order

### Key Characteristics

✅ **Exponential forgetting**: Simple e^(-t/stability) decay model, no ML dependencies

✅ **Diminishing returns**: High PKR gains less from success, reflects learning saturation

✅ **Stability tracking**: Memory consolidation improves with successful reviews

✅ **Bounded values**: PKR ∈ [0, 1], stability ∈ [0.1, 10.0], forgetting ∈ [0, 1]

✅ **Deterministic**: Same inputs always produce same outputs

✅ **Importance amplification**: Critical nodes get higher weakness scores

✅ **Comprehensive testing**: 42 tests covering creation, validation, reviews, forgetting, weakness, and integration scenarios

---

## Phase 4: Question Bank & Tagging System ✅

**Status**: Complete

### Overview

Phase 4 extends the Question model with difficulty ratings and tagging support, and introduces the **QuestionBank** class for managing collections of questions with advanced query capabilities and graph-based coverage validation.

### Question Model Enhancements

**New Fields:**
- `difficulty`: Integer rating from 1 (easiest) to 5 (hardest), defaults to 3
- `tags`: Set of string tags for categorization (e.g., `{"basics", "syntax"}`)
- `last_attempted_at`: Optional datetime tracking when question was last attempted

**New Methods:**
- `record_attempt(success: bool, timestamp: datetime)`: Records attempt and updates both metadata (hits/misses) and last_attempted_at

### QuestionBank Class

Centralized question repository with validation and query capabilities.

**Core Operations:**
```python
bank = QuestionBank()

# Add questions (with optional graph validation)
bank.add_question(question)
bank.add_question(question, graph=graph)  # Validates coverage

# Remove questions
bank.remove_question("q1")

# Retrieve questions
question = bank.get_question("q1")
count = bank.count_questions()
```

**Coverage Validation:**

When adding a question with a graph:
1. Ensures all `covered_node_ids` exist in the graph
2. For multi-node coverage, validates nodes form a connected subgraph using `graph.is_valid_coverage()`
3. Raises `ValueError` if validation fails

**Query Methods:**

```python
# By node coverage
python_questions = bank.get_questions_by_node("python")

# By tag
basics_questions = bank.get_questions_by_tag("basics")

# By difficulty range
easy_questions = bank.get_questions_by_difficulty(1, 2)
hard_questions = bank.get_questions_by_difficulty(4, 5)

# By question type
flashcards = bank.get_questions_by_type(QuestionType.FLASHCARD)
```

**Performance Tracking:**

```python
# Record successful answer
bank.record_question_success("q1", datetime.now())

# Record failed answer
bank.record_question_failure("q1", datetime.now())
```

Both methods:
- Update question metadata (hits/misses)
- Update `last_attempted_at` timestamp
- Raise `KeyError` if question not found

### Example Usage

```python
from src.models import QuestionBank, Question, Graph, Node, Edge, EdgeType

# Build knowledge graph
graph = Graph()
graph.add_node(Node(id="python", topic_name="Python"))
graph.add_node(Node(id="variables", topic_name="Variables"))
graph.add_edge(Edge(
    from_node_id="python",
    to_node_id="variables",
    type=EdgeType.PREREQUISITE,
    weight=1.0
))

# Create question bank
bank = QuestionBank()

# Add questions with tags and difficulty
q1 = Question(
    id="q1",
    text="What is Python?",
    answer="A high-level programming language",
    covered_node_ids=["python"],
    difficulty=1,
    tags={"basics", "intro"},
    # ... other required fields
)

q2 = Question(
    id="q2",
    text="How do you declare a variable?",
    answer="name = value",
    covered_node_ids=["variables"],
    difficulty=2,
    tags={"basics", "syntax"},
    # ... other required fields
)

# Add with graph validation
bank.add_question(q1, graph=graph)
bank.add_question(q2, graph=graph)

# Query by tags
basics = bank.get_questions_by_tag("basics")  # Returns [q1, q2]

# Query by difficulty
easy = bank.get_questions_by_difficulty(1, 2)  # Returns [q1, q2]
```

### Testing

```bash
# Run Phase 4 tests only
pytest tests/test_question_bank.py -v

# Run all tests (Phases 1-4)
pytest tests/ -v
```

**Test Coverage:**
- 31 comprehensive tests across 6 test classes
- Question enhancements (difficulty, tags, last_attempted_at)
- CRUD operations
- Coverage validation with graph integration
- Query methods (by node, tag, difficulty, type)
- Performance tracking
- Integration test with realistic learning scenario

### Key Design Decisions

✅ **Graph Integration**: Coverage validation uses Phase 2's `is_valid_coverage()` with configurable max_hops (default: 3) and all edge types

✅ **Optional Validation**: Questions can be added without graph validation for flexibility

✅ **Immutable Queries**: All query methods return new lists, not references to internal storage

✅ **Type Safety**: Uses Pydantic validation for difficulty ranges (1-5) and non-empty tags

✅ **Performance Tracking**: `record_attempt()` updates both metadata and timestamp atomically

✅ **Simple Queries**: No complex ranking, sorting, or priority queues—query results returned in insertion order

### Constraints

- Difficulty must be 1-5 (validated by Pydantic)
- Tags must be non-empty strings
- Coverage validation requires max_hops=3 and checks all edge types
- Question IDs must be unique within bank
- No implicit question generation or LLM integration

---

## Next Phases (Not Yet Implemented)

**Phase 5**: Graph-based Question Selection
- Combine graph reasoning with user knowledge state
- Smart question prioritization based on weakness, graph structure, and learning paths
- Coverage-aware selection algorithms

**Phase 6**: Persistence Layer
- Database models and repositories
- Data access patterns

**Phase 6**: API Layer
- RESTful API endpoints
- Request/response models

**Phase 7**: Frontend UI
- Interactive graph visualization
- Question interface
- Progress tracking

