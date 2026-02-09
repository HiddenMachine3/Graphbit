# Project-Based Refactor - Summary

## Overview
This refactor introduces **Project** as the primary owner of knowledge graphs, nodes, edges, materials, and questions. Communities now reference projects and apply overrides rather than owning content directly.

---

## ✅ COMPLETED BACKEND CHANGES

### 1. Core Models Updated

#### New Model
- **`Project`** ([project.py](Backend/app/domain/project.py))
  - Fields: `id`, `name`, `description`, `owner_id`, `visibility`, `created_at`, `updated_at`
  - Visibility: `PRIVATE`, `SHARED`, `PUBLIC`
  - Exported in `__init__.py`

#### Updated Models (added `project_id`)
- ✅ **`Graph`** - Now has `project_id` field
- ✅ **`Node`** - Now has `project_id` field
- ✅ **`Edge`** - Now has `project_id` field
- ✅ **`Question`** - Now has `project_id` field
- ✅ **`Material`** - Now has `project_id` field
- ✅ **`UserNodeState`** - Now has `project_id` field
- ✅ **`ContentSession`** - Now has `project_id` field
- ✅ **`RevisionSession`** - Constructor now accepts `project_id` parameter

#### Community Model Refactored
- ✅ **`Community`** ([community.py](Backend/app/domain/community.py))
  - Added `project_ids: set[str]` - many-to-many relationship with projects
  - Changed `node_importance_overrides` from `dict[str, float]` to `dict[str, dict[str, float]]`
    - Now structured as: `project_id -> node_id -> importance`
  - Added `question_importance_overrides: dict[str, dict[str, float]]`
    - Structured as: `project_id -> question_id -> importance`
  - New methods:
    - `add_project(project_id)`
    - `remove_project(project_id)`
    - `set_node_importance(project_id, node_id, importance)`
    - `set_question_importance(project_id, question_id, importance)`
    - `get_node_importance(project_id, node_id)`
    - `get_question_importance(project_id, question_id)`
  - Communities NO LONGER own graphs or questions directly

### 2. Algorithms Updated (Project-Aware)

#### Community Features ([community_features.py](Backend/app/domain/community_features.py))
- ✅ `CommunityContext.get_effective_importance()` - Now takes `project_id` parameter
- ✅ `CommunityContext.filter_questions()` - Now takes `project_id` parameter
- ✅ `select_next_question_for_community()` - Now takes `project_id` parameter
- ✅ `compute_user_progress_in_community()` - Now takes `project_id` parameter
- ✅ `compute_leaderboard()` - Now takes `project_id` parameter

#### Other Algorithms (No Changes Needed)
- ✅ **Clustering** ([clustering.py](Backend/app/domain/clustering.py)) - Works with user_node_states and importance_lookup (already scoped)
- ✅ **Ranking** ([ranking.py](Backend/app/domain/ranking.py)) - Works with clusters and importance_lookup (already scoped)
- ✅ **Interjection** ([interjection.py](Backend/app/domain/interjection.py)) - Works with graph and question_bank (already scoped)
- ✅ **Revision Planner** - Works with user_node_states (already scoped)

### 3. Seeding Script Rewritten ([seed_data.py](Backend/seed_data.py))

✅ **New Structure:**
```
1 User (Alice Johnson)
 ↓
3 Projects:
  - Python Programming (5 nodes, 3 questions)
  - Data Structures & Algorithms (4 nodes, 3 questions)
  - Biology Fundamentals (4 nodes, 3 questions)
 ↓
1 Community (Learning Hub)
  - Attached to all 3 projects
  - Community overrides per project:
    * Python: py_basics (1.2), py_variables (1.1)
    * DSA: dsa_trees (1.5), dsa_sorting (1.3)
    * Biology: bio_dna (1.4)
```

Each project has:
- Graph with nodes and edges
- Questions linked to nodes
- UserNodeState for each node
- Community importance overrides

### 4. Tests Updated

✅ **Test Infrastructure:**
- Added fixtures to `conftest.py`:
  - `test_project_id()` - Default test project ID
  - `test_project()` - Complete test Project object

✅ **Tests Started:**
- `test_models.py` - Updated Node creation tests to include `project_id`
- Other test files will need similar updates (systematic find-replace of model constructors)

---

## ✅ COMPLETED FRONTEND CHANGES

### 1. Types Updated ([lib/types.ts](frontend/lib/types.ts))

✅ **New Type:**
```typescript
export interface ProjectDTO {
  id: string;
  name: string;
  description: string;
  owner_id: string;
  visibility: "private" | "shared" | "public";
  created_at: string;
  updated_at: string;
}
```

✅ **Updated Types** (added `project_id`):
- `NodeDTO`
- `GraphEdgeDTO`
- `QuestionDTO`

### 2. Global Store Updated ([lib/store.ts](frontend/lib/store.ts))

✅ **New State:**
```typescript
{
  currentProjectId: string | null;
  currentProjectName: string | null;
  setCurrentProjectId: (id: string | null) => void;
  setCurrentProjectName: (name: string | null) => void;
  // ... existing community/session state
}
```

### 3. UI Components Created

✅ **ProjectSwitcher** ([components/ProjectSwitcher.tsx](frontend/components/ProjectSwitcher.tsx))
- Fetches all projects from `/api/v1/projects`
- Displays dropdown selector
- Updates global store on selection
- Auto-selects first project if none selected

✅ **Topbar Updated** ([components/Topbar.tsx](frontend/components/Topbar.tsx))
- Now includes `<ProjectSwitcher />` component
- Displayed next to app logo in header

### 4. API Client Started

✅ **Project API** ([lib/api/project.ts](frontend/lib/api/project.ts))
- `getProjects()` - List all projects
- `getProject(projectId)` - Get single project
- `createProject()` - Create new project
- `updateProject()` - Update project metadata
- `deleteProject()` - Delete project

---

## ⏳ REMAINING WORK

### Backend

1. **Update remaining test files** (systematic update needed):
   - `test_graph_reasoning.py` - Add `project_id` to all Node/Edge/Graph creations
   - `test_ranking.py` - Add `project_id` to questions and nodes
   - `test_revision_session.py` - Add `project_id` to RevisionSession construction
   - `test_community_features.py` - Update community tests for new override structure
   - `test_weak_node_clustering.py` - Add `project_id` to UserNodeState
   - `test_interjection.py` - Add `project_id` to models
   - `test_ingestion.py` - Add `project_id` to nodes/graphs
   - Pattern: Find all instances of model constructors and add `project_id="test_project_1"`

2. **API Routes** (need to be created/updated):
   - `GET /api/v1/projects` - List projects
   - `POST /api/v1/projects` - Create project
   - `GET /api/v1/projects/{project_id}` - Get project
   - `PATCH /api/v1/projects/{project_id}` - Update project
   - `DELETE /api/v1/projects/{project_id}` - Delete project
   - Update existing routes to accept `project_id` query parameter or path parameter:
     - `/graph` → `/projects/{project_id}/graph`
     - `/graph/nodes` → `/projects/{project_id}/nodes`
     - `/questions` → `/projects/{project_id}/questions`
     - `/session` → `/projects/{project_id}/session`

3. **Database Models** (if using ORM):
   - Create `Project` table/model
   - Add `project_id` foreign keys to existing tables
   - Migration scripts for adding `project_id` columns

### Frontend

1. **Update API client functions** to include `project_id`:
   - `graph.ts` - All functions need project_id parameter
   - `session.ts` - Session functions need project_id
   - `material.ts` - Material functions need project_id
   - `revision.ts` - Revision functions need project_id
   - `community.ts` - May need updates for new override structure

2. **Update pages** to be project-aware:
   - `/graph/page.tsx` - Filter graph by currentProjectId from store
   - `/session/page.tsx` - Scope session to currentProjectId
   - `/materials/page.tsx` - Filter materials by currentProjectId
   - `/communities/page.tsx` - Show project-community relationships

3. **Update graph visualization**:
   - Graph components should reload when currentProjectId changes
   - Add useEffect watching currentProjectId in graph components
   - Clear/reload graph data on project switch

4. **Update session & material flows**:
   - Session creation should include project_id
   - Material upload should be scoped to a project
   - Revision feedback should update project-specific user states

---

## 🎯 MIGRATION CHECKLIST

### Before Running
- [ ] Update database schema (add project_id columns, create projects table)
- [ ] Run database migrations
- [ ] Update all remaining test files
- [ ] Create API routes for projects

### Testing
- [ ] Run backend tests: `pytest`
- [ ] Verify seeding script works: `python Backend/seed_data.py --reset`
- [ ] Test project creation/switching in UI
- [ ] Verify graph switches when changing projects
- [ ] Verify community overrides work per-project

### Deployment
- [ ] Backend compiles and all tests pass
- [ ] Frontend builds without errors: `npm run build`
- [ ] Seed database with test data
- [ ] Verify user can switch between projects
- [ ] Verify community features work with new structure

---

## 🔧 QUICK REFERENCE

### Creating Test Objects

```python
# Backend tests
from backend.app.domain import Project, Node, Graph, Question, UserNodeState
from datetime import datetime

project = Project(
    id="test_proj",
    name="Test",
    description="",
    owner_id="user1",
    visibility=ProjectVisibility.PRIVATE,
    created_at=datetime.now(),
    updated_at=datetime.now()
)

node = Node(
    id="node1",
    project_id="test_proj",
    topic_name="Test Topic"
)

graph = Graph(project_id="test_proj")
```

### Community Override Access

```python
# Old way (removed)
community.node_importance_overrides["node1"] = 1.5

# New way
community.set_node_importance("project1", "node1", 1.5)
override = community.get_node_importance("project1", "node1")
```

### Frontend Project Access

```typescript
// Get current project
const { currentProjectId, currentProjectName } = useAppStore();

// Fetch project data
const project = await getProject(currentProjectId);

// API calls with project
const graph = await fetchGraphSummary(currentProjectId);
```

---

## 📝 NOTES

### Design Decisions

1. **Projects own content, Communities apply overrides**
   - Projects: primary owners of graphs, nodes, questions
   - Communities: social layer that references projects and customizes importance

2. **Nested override structure**
   - `community.node_importance_overrides[project_id][node_id] = importance`
   - Allows same community to have different priorities per project

3. **Algorithms unchanged**
   - Core algorithms (clustering, ranking, session) still work the same
   - Only their inputs are now scoped by project_id
   - Maintains determinism and test compatibility

4. **Backward compatibility**
   - Tests need updates but algorithms don't
   - Seeding script generates valid test data
   - Migration path is clear (add project_id everywhere)

### Common Patterns

**Test file updates:**
```python
# Find: Node(id="x", topic_name="y")
# Replace: Node(id="x", project_id="test_project_1", topic_name="y")

# Find: Graph()
# Replace: Graph(project_id="test_project_1")

# Find: RevisionSession(user_id, graph, ...)
# Replace: RevisionSession(user_id, "test_project_1", graph, ...)
```
