# Phase 4: Question Bank & Tagging System

**Status**: ✅ Complete  
**Date**: February 2026  
**Tests**: 31 tests (177 total)

## Overview

Phase 4 extends the Question model with difficulty ratings and tagging capabilities, and introduces the **QuestionBank** class for managing collections of questions with advanced query and validation features.

## Core Features

### 1. Question Model Enhancements

**New Fields:**
- `difficulty: int` — Rating from 1 (easiest) to 5 (hardest), defaults to 3
- `tags: set[str]` — Flexible categorization tags (e.g., `{"basics", "syntax"}`)
- `last_attempted_at: Optional[datetime]` — Timestamp of last attempt

**New Methods:**
- `record_attempt(success: bool, timestamp: datetime)` — Records attempt and updates:
  - Question metadata (hits/misses)
  - Last attempted timestamp

**Validation:**
- Difficulty constrained to [1, 5] via Pydantic
- Tags must be non-empty strings
- Tags validator ensures no empty strings in set

### 2. QuestionBank Class

Centralized question repository with validation and query capabilities.

**Storage:**
```python
questions: dict[str, Question]  # question_id -> Question
```

**Core Operations:**

| Method | Description |
|--------|-------------|
| `add_question(question, graph=None)` | Add question with optional coverage validation |
| `remove_question(question_id)` | Remove question by ID |
| `get_question(question_id)` | Retrieve question by ID |
| `count_questions()` | Get total question count |

**Query Methods:**

| Method | Parameters | Returns |
|--------|-----------|---------|
| `get_questions_by_node(node_id)` | `node_id: str` | Questions covering that node |
| `get_questions_by_tag(tag)` | `tag: str` | Questions with that tag |
| `get_questions_by_difficulty(min_diff, max_diff)` | `min_diff, max_diff: int` | Questions in difficulty range |
| `get_questions_by_type(question_type)` | `question_type: QuestionType` | Questions of that type |

**Performance Tracking:**

| Method | Description |
|--------|-------------|
| `record_question_success(question_id, timestamp)` | Record correct answer |
| `record_question_failure(question_id, timestamp)` | Record incorrect answer |

### 3. Coverage Validation

When adding a question with `graph` parameter:

1. **Node Existence Check**: All `covered_node_ids` must exist in graph
2. **Connectivity Check**: For multi-node coverage, validates using `graph.is_valid_coverage()`:
   - `max_hops = 3`
   - `allowed_edge_types = {PREREQUISITE, DEPENDS_ON, APPLIED_WITH, SUBCONCEPT_OF}`
3. **Error Handling**: Raises `ValueError` with descriptive messages if validation fails

**Example:**
```python
# Valid: nodes are connected
q = Question(covered_node_ids=["python", "variables"], ...)
bank.add_question(q, graph=graph)  # Success

# Invalid: nodes are disconnected
q = Question(covered_node_ids=["python", "java"], ...)
bank.add_question(q, graph=graph)  # ValueError: coverage is not valid
```

## Implementation Details

### Question Enhancements

**File**: `src/models.py` (lines ~470-510)

```python
class Question(BaseModel):
    # ... existing fields ...
    
    # Phase 4 additions
    difficulty: int = Field(default=3, ge=1, le=5)
    tags: set[str] = Field(default_factory=set)
    last_attempted_at: Optional[datetime] = None
    
    @field_validator("tags")
    def validate_tags(cls, v: set[str]) -> set[str]:
        """Ensure all tags are non-empty strings."""
        if any(tag.strip() == "" for tag in v):
            raise ValueError("Tags cannot be empty strings")
        return v
    
    def record_attempt(self, success: bool, timestamp: datetime) -> None:
        """Record question attempt and update metadata."""
        if success:
            self.metadata.record_hit()
        else:
            self.metadata.record_miss()
        self.last_attempted_at = timestamp
```

### QuestionBank Class

**File**: `src/models.py` (lines ~800-1005)

Key design decisions:

1. **Simple Storage**: Dict-based storage by question ID
2. **Immutable Returns**: Query methods return new lists (no internal state leaks)
3. **Optional Validation**: Graph validation only when `graph` parameter provided
4. **Integration**: Uses Phase 2's `is_valid_coverage()` for connectivity checks
5. **No Sorting**: Query results returned in insertion order (dict insertion order)

## Testing Strategy

**File**: `tests/test_question_bank.py` (520 lines, 31 tests)

### Test Structure

| Test Class | Tests | Focus |
|-----------|-------|-------|
| `TestQuestionEnhancements` | 10 | Difficulty, tags, last_attempted_at, record_attempt |
| `TestQuestionBankBasics` | 7 | CRUD operations, duplicate detection |
| `TestCoverageValidation` | 4 | Graph integration, valid/invalid coverage |
| `TestQuestionBankQueries` | 5 | Query methods (node, tag, difficulty, type) |
| `TestPerformanceTracking` | 4 | Success/failure recording, mixed performance |
| `TestQuestionBankIntegration` | 1 | Realistic Python learning scenario |

### Helper Functions

Created to handle Pydantic required fields:

```python
def create_metadata(**kwargs):
    """Create QuestionMetadata with defaults."""
    defaults = {"created_by": "test_user", "created_at": datetime.now()}
    defaults.update(kwargs)
    return QuestionMetadata(**defaults)

def create_question(question_id="q1", **kwargs):
    """Create Question with defaults."""
    if "metadata" not in kwargs:
        kwargs["metadata"] = create_metadata()
    defaults = {
        "id": question_id,
        "text": "Test question",
        "answer": "Test answer",
        "question_type": QuestionType.FLASHCARD,
        "knowledge_type": KnowledgeType.CONCEPT,
        "covered_node_ids": ["node1"],
    }
    defaults.update(kwargs)
    return Question(**defaults)

def create_edge(from_id, to_id, edge_type=EdgeType.PREREQUISITE, weight=1.0):
    """Create Edge with defaults."""
    return Edge(from_node_id=from_id, to_node_id=to_id, type=edge_type, weight=weight)
```

## Demonstration

**File**: `demos/demo_phase4.py` (596 lines)

### Demo Scenarios

1. **Question Enhancements**
   - Create question with difficulty and tags
   - Record multiple attempts
   - Show success rate tracking

2. **QuestionBank CRUD**
   - Add, retrieve, remove questions
   - Duplicate detection

3. **Coverage Validation**
   - Valid single-node coverage
   - Valid multi-node connected coverage
   - Invalid disconnected coverage
   - Invalid nonexistent nodes

4. **Query Methods**
   - By node coverage
   - By tag
   - By difficulty range
   - By question type

5. **Performance Tracking**
   - Record success/failure over time
   - Track last attempted timestamp

6. **Realistic Python Learning Bank**
   - 9 questions across 6 nodes
   - Beginner to advanced difficulty
   - Multiple tags and question types
   - Statistics and categorization

## Key Constraints

✅ **No Ranking Logic**: Questions returned in insertion order  
✅ **No Priority Queues**: Simple query methods only  
✅ **No Sessions**: Stateless question management  
✅ **No LLM Generation**: Manual question creation only  
✅ **Simple Coverage**: Fixed max_hops=3, all edge types  

## Integration with Previous Phases

### Phase 1 (Domain Models)
- Extends `Question` model
- Uses existing `QuestionMetadata.record_hit()` and `record_miss()`
- Leverages Pydantic validation framework

### Phase 2 (Graph Reasoning)
- Uses `Graph.is_valid_coverage()` for multi-node validation
- Checks `Graph.nodes` for existence validation
- Respects edge types and hop limits

### Phase 3 (User Knowledge State)
- Questions now track `last_attempted_at` for forgetting calculations
- Performance data (hits/misses) feeds into user state updates
- Difficulty ratings can inform adaptive learning (future phase)

## Test Results

```bash
$ pytest tests/test_question_bank.py -v
31 passed in 0.46s

$ pytest tests/ -v
177 passed in 0.97s
```

**Coverage:**
- Phase 1: 59 tests ✅
- Phase 2: 45 tests ✅
- Phase 3: 42 tests ✅
- Phase 4: 31 tests ✅
- **Total: 177 tests passing**

## Files Changed

| File | Lines | Change |
|------|-------|--------|
| `src/models.py` | +215 | Question enhancements + QuestionBank class |
| `tests/test_question_bank.py` | +520 | Complete test suite |
| `demos/demo_phase4.py` | +596 | 6 demonstration scenarios |
| `README.md` | +160 | Phase 4 documentation |

## Lessons Learned

### 1. Pydantic Strictness
**Issue**: Tests initially failed because `QuestionMetadata` requires `created_by` and `created_at`  
**Solution**: Created helper functions to provide defaults for all required fields  
**Takeaway**: Always check model requirements before writing tests

### 2. Method vs Property
**Issue**: Demo tried to access `metadata.success_rate` (doesn't exist)  
**Solution**: `success_rate` is a computed property on `Question`, not `QuestionMetadata`  
**Takeaway**: Understand model hierarchy and where computed properties live

### 3. Graph Integration Signature
**Issue**: `is_valid_coverage()` requires `max_hops` and `allowed_edge_types`  
**Solution**: Added default parameters (max_hops=3, all edge types) to QuestionBank  
**Takeaway**: When integrating across phases, verify exact method signatures

### 4. None Handling in Demos
**Issue**: `success_rate` returns `None` when no attempts, formatting failed  
**Solution**: Check for None/zero attempts before formatting  
**Takeaway**: Demo code needs robust None/empty state handling

## Next Phase: Question Selection

**Phase 5** will combine:
- QuestionBank query capabilities (Phase 4)
- Graph reasoning (Phase 2)
- User knowledge state (Phase 3)

To implement:
- Smart question prioritization
- Weakness-based selection
- Coverage-aware algorithms
- Learning path optimization

## Conclusion

Phase 4 successfully extends the Question model and introduces a robust QuestionBank system with:

✅ Flexible tagging and difficulty ratings  
✅ Graph-based coverage validation  
✅ Comprehensive query capabilities  
✅ Performance tracking integration  
✅ 31 comprehensive tests (100% passing)  
✅ Full backward compatibility with Phases 1-3  

The system is now ready for intelligent question selection algorithms in Phase 5.
