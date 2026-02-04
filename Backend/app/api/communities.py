"""Community management API endpoints."""

from fastapi import APIRouter
from app.domain import Community

router = APIRouter()

# In-memory storage for demo (replace with database queries)
_communities = {
    "python_fundamentals": Community(
        id="python_fundamentals",
        name="Python Fundamentals",
        description="Learn the basics of Python programming",
        node_importance_overrides={"python_basics": 1.0, "variables": 1.0, "functions": 0.8}
    ),
    "advanced_python": Community(
        id="advanced_python",
        name="Advanced Python",
        description="Master advanced concepts like OOP and decorators",
        node_importance_overrides={"oop": 1.5, "classes": 1.5, "decorators": 1.2, "inheritance": 1.0}
    ),
    "async_programming": Community(
        id="async_programming",
        name="Async Programming",
        description="Learn concurrent and asynchronous programming",
        node_importance_overrides={"async": 2.0, "functions": 1.0}
    ),
}

_active_community = "python_fundamentals"


@router.get("/communities")
async def list_communities():
    """List all available communities."""
    return [
        {
            "id": c.id,
            "name": c.name,
            "description": c.description,
            "node_importance_overrides": c.node_importance_overrides,
        }
        for c in _communities.values()
    ]


@router.get("/communities/{community_id}")
async def get_community(community_id: str):
    """Get a specific community."""
    if community_id not in _communities:
        return {"error": "Community not found"}, 404
    
    c = _communities[community_id]
    return {
        "id": c.id,
        "name": c.name,
        "description": c.description,
        "node_importance_overrides": c.node_importance_overrides,
    }


@router.post("/communities/active")
async def set_active_community(data: dict):
    """Set the active community."""
    global _active_community
    community_id = data.get("community_id")
    if community_id not in _communities:
        return {"error": "Community not found"}, 404
    
    _active_community = community_id
    return {"community_id": community_id}


@router.get("/communities/{community_id}/progress")
async def get_community_progress(community_id: str):
    """Get progress metrics for a community."""
    if community_id not in _communities:
        return {"error": "Community not found"}, 404
    
    # Mock progress data
    progress_map = {
        "python_fundamentals": {"overall_progress": 0.68, "relevant_topics": 12},
        "advanced_python": {"overall_progress": 0.42, "relevant_topics": 8},
        "async_programming": {"overall_progress": 0.35, "relevant_topics": 5},
    }
    
    progress = progress_map.get(community_id, {"overall_progress": 0.5, "relevant_topics": 5})
    return {
        "community_id": community_id,
        "overall_progress": progress["overall_progress"],
        "relevant_topics": progress["relevant_topics"],
    }


@router.get("/communities/{community_id}/leaderboard")
async def get_community_leaderboard(community_id: str):
    """Get leaderboard for a community."""
    if community_id not in _communities:
        return {"error": "Community not found"}, 404
    
    # Mock leaderboard data
    leaderboard_map = {
        "python_fundamentals": [
            {"user_id": "alice", "score": 0.8, "rank": 1},
            {"user_id": "charlie", "score": 0.7, "rank": 2},
            {"user_id": "bob", "score": 0.6, "rank": 3},
        ],
        "advanced_python": [
            {"user_id": "bob", "score": 0.75, "rank": 1},
            {"user_id": "charlie", "score": 0.65, "rank": 2},
            {"user_id": "alice", "score": 0.55, "rank": 3},
        ],
        "async_programming": [
            {"user_id": "bob", "score": 0.7, "rank": 1},
            {"user_id": "alice", "score": 0.5, "rank": 2},
        ],
    }
    
    return leaderboard_map.get(community_id, [])
