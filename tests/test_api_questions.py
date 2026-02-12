"""API tests for question CRUD."""


def test_question_crud(api_client):
    project_resp = api_client.post(
        "/api/v1/projects",
        json={
            "id": "proj-q",
            "name": "Question Project",
            "description": "Project for questions",
            "visibility": "private",
        },
    )
    assert project_resp.status_code == 200

    create_resp = api_client.post(
        "/api/v1/questions",
        json={
            "id": "q-1",
            "project_id": "proj-q",
            "text": "What is Stoicism?",
            "answer": "A philosophy of virtue and reason.",
            "question_type": "OPEN",
            "knowledge_type": "CONCEPT",
            "covered_node_ids": ["stoic_foundations"],
            "difficulty": 2,
            "tags": ["stoicism"],
        },
    )
    assert create_resp.status_code == 200
    created = create_resp.json()
    assert created["project_id"] == "proj-q"

    list_resp = api_client.get("/api/v1/questions", params={"project_id": "proj-q"})
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1

    get_resp = api_client.get("/api/v1/questions/q-1")
    assert get_resp.status_code == 200
    assert get_resp.json()["text"] == "What is Stoicism?"

    update_resp = api_client.patch(
        "/api/v1/questions/q-1",
        json={"difficulty": 4},
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["difficulty"] == 4

    delete_resp = api_client.delete("/api/v1/questions/q-1")
    assert delete_resp.status_code == 200

    missing_resp = api_client.get("/api/v1/questions/q-1")
    assert missing_resp.status_code == 404


def test_question_suggestions_raw_text_returns_candidates(api_client, monkeypatch):
    project_resp = api_client.post(
        "/api/v1/projects",
        json={
            "id": "proj-q-suggest-raw",
            "name": "Question Suggest Raw",
            "description": "Project for question raw-text suggestions",
            "visibility": "private",
        },
    )
    assert project_resp.status_code == 200

    node_resp = api_client.post(
        "/api/v1/graph/nodes",
        json={
            "project_id": "proj-q-suggest-raw",
            "topic_name": "Graph Basics",
            "importance": 0.6,
            "relevance": 0.6,
        },
    )
    assert node_resp.status_code == 200
    node_id = node_resp.json()["id"]

    class FakeInferenceClient:
        def __init__(self, *args, **kwargs):
            pass

        def feature_extraction(self, text, model=None):
            return [0.1] * 768

        def token_classification(self, text, model=None):
            return [{"word": "graph"}]

    class FakeRepo:
        def __init__(self, db):
            self.db = db

        async def get_material_text(self, material_id: str) -> str:
            return "Graph theory basics"

        async def save_material_embedding(self, material_id: str, embedding: list[float]) -> None:
            return None

        async def search_nodes_vector(self, project_id: str, embedding: list[float], top_k: int):
            from app.services.node_suggestions.types import NodeMatch
            return [NodeMatch(node_id=node_id, score=0.95, source="vector")]

        async def search_nodes_fts(self, project_id: str, query: str, top_k: int):
            from app.services.node_suggestions.types import NodeMatch
            return [NodeMatch(node_id=node_id, score=0.9, source="keyword")]

        async def list_nodes(self, project_id: str):
            return [node_id]

        async def store_suggestions(self, material_id: str, suggestions):
            return None

        async def max_similarity_to_nodes(self, project_id: str, candidate_embedding: list[float]) -> float:
            return 0.1

    monkeypatch.setenv("HF_TOKEN", "test-token")
    monkeypatch.setattr(
        "huggingface_hub.InferenceClient",
        FakeInferenceClient,
    )
    monkeypatch.setattr(
        "app.api.questions.PostgresNodeSuggestionRepository",
        FakeRepo,
    )

    suggest_resp = api_client.post(
        "/api/v1/questions/suggestions/raw-text",
        json={
            "project_id": "proj-q-suggest-raw",
            "text": "Graph traversal and graph basics",
            "threshold": 0.75,
            "semantic_weight": 0.6,
            "keyword_weight": 0.4,
            "top_k": 20,
        },
    )
    assert suggest_resp.status_code == 200
    payload = suggest_resp.json()
    assert "strong" in payload
    assert "weak" in payload
    assert any(item["node_id"] == node_id for item in payload["strong"])


def test_question_suggestions_raw_text_missing_project_id(api_client, monkeypatch):
    class FakeInferenceClient:
        def __init__(self, *args, **kwargs):
            pass

        def feature_extraction(self, text, model=None):
            return [0.1] * 768

        def token_classification(self, text, model=None):
            return [{"word": "graph"}]

    monkeypatch.setenv("HF_TOKEN", "test-token")
    monkeypatch.setattr(
        "huggingface_hub.InferenceClient",
        FakeInferenceClient,
    )

    suggest_resp = api_client.post(
        "/api/v1/questions/suggestions/raw-text",
        json={"text": "Graph traversal"},
    )
    assert suggest_resp.status_code == 400


def test_question_suggestions_wrapper_matches_raw_text(api_client, monkeypatch):
    project_resp = api_client.post(
        "/api/v1/projects",
        json={
            "id": "proj-q-wrapper",
            "name": "Question Wrapper",
            "description": "Project for wrapper parity",
            "visibility": "private",
        },
    )
    assert project_resp.status_code == 200

    node_resp = api_client.post(
        "/api/v1/graph/nodes",
        json={
            "project_id": "proj-q-wrapper",
            "topic_name": "Binary Search",
            "importance": 0.6,
            "relevance": 0.6,
        },
    )
    assert node_resp.status_code == 200
    node_id = node_resp.json()["id"]

    question_resp = api_client.post(
        "/api/v1/questions",
        json={
            "id": "q-wrapper-1",
            "project_id": "proj-q-wrapper",
            "text": "How does binary search reduce complexity?",
            "answer": "By halving the search space each step.",
            "question_type": "OPEN",
            "knowledge_type": "CONCEPT",
            "covered_node_ids": [],
            "difficulty": 1,
            "tags": [],
        },
    )
    assert question_resp.status_code == 200

    class FakeInferenceClient:
        def __init__(self, *args, **kwargs):
            pass

        def feature_extraction(self, text, model=None):
            return [0.1] * 768

        def token_classification(self, text, model=None):
            return [{"word": "binary"}, {"word": "search"}]

    class FakeRepo:
        def __init__(self, db):
            self.db = db

        async def get_material_text(self, material_id: str) -> str:
            return ""

        async def save_material_embedding(self, material_id: str, embedding: list[float]) -> None:
            return None

        async def search_nodes_vector(self, project_id: str, embedding: list[float], top_k: int):
            from app.services.node_suggestions.types import NodeMatch
            return [NodeMatch(node_id=node_id, score=0.95, source="vector")]

        async def search_nodes_fts(self, project_id: str, query: str, top_k: int):
            from app.services.node_suggestions.types import NodeMatch
            return [NodeMatch(node_id=node_id, score=0.9, source="keyword")]

        async def list_nodes(self, project_id: str):
            return [node_id]

        async def store_suggestions(self, material_id: str, suggestions):
            return None

        async def max_similarity_to_nodes(self, project_id: str, candidate_embedding: list[float]) -> float:
            return 0.1

    monkeypatch.setenv("HF_TOKEN", "test-token")
    monkeypatch.setattr(
        "huggingface_hub.InferenceClient",
        FakeInferenceClient,
    )
    monkeypatch.setattr(
        "app.api.questions.PostgresNodeSuggestionRepository",
        FakeRepo,
    )

    wrapper_resp = api_client.post(
        "/api/v1/questions/q-wrapper-1/suggestions",
        json={
            "project_id": "proj-q-wrapper",
            "threshold": 0.75,
            "semantic_weight": 0.6,
            "keyword_weight": 0.4,
            "top_k": 20,
        },
    )
    assert wrapper_resp.status_code == 200

    raw_resp = api_client.post(
        "/api/v1/questions/suggestions/raw-text",
        json={
            "project_id": "proj-q-wrapper",
            "text": "How does binary search reduce complexity?\n\nBy halving the search space each step.",
            "threshold": 0.75,
            "semantic_weight": 0.6,
            "keyword_weight": 0.4,
            "top_k": 20,
        },
    )
    assert raw_resp.status_code == 200

    wrapper_payload = wrapper_resp.json()
    raw_payload = raw_resp.json()
    assert len(wrapper_payload["strong"]) == len(raw_payload["strong"])
    assert len(wrapper_payload["weak"]) == len(raw_payload["weak"])
