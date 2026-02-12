"""API tests for material CRUD."""


def test_material_crud(api_client):
    project_resp = api_client.post(
        "/api/v1/projects",
        json={
            "id": "proj-m",
            "name": "Material Project",
            "description": "Project for materials",
            "visibility": "private",
        },
    )
    assert project_resp.status_code == 200

    create_resp = api_client.post(
        "/api/v1/materials",
        json={
            "id": "mat-1",
            "project_id": "proj-m",
            "title": "Test Material",
            "content_text": "Line one\n\nLine two",
        },
    )
    assert create_resp.status_code == 200
    created = create_resp.json()
    assert created["project_id"] == "proj-m"
    assert created["chunk_count"] == 2

    list_resp = api_client.get("/api/v1/materials", params={"project_id": "proj-m"})
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1

    get_resp = api_client.get("/api/v1/materials/mat-1")
    assert get_resp.status_code == 200
    material = get_resp.json()
    assert material["title"] == "Test Material"
    assert len(material["chunks"]) == 2

    update_resp = api_client.patch(
        "/api/v1/materials/mat-1",
        json={"title": "Updated Title", "content_text": "Updated content"},
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["title"] == "Updated Title"
    assert update_resp.json()["chunk_count"] == 1

    delete_resp = api_client.delete("/api/v1/materials/mat-1")
    assert delete_resp.status_code == 200

    missing_resp = api_client.get("/api/v1/materials/mat-1")
    assert missing_resp.status_code == 404


def test_material_attach(api_client):
    project_resp = api_client.post(
        "/api/v1/projects",
        json={
            "id": "proj-attach",
            "name": "Attach Project",
            "description": "Project for material attach",
            "visibility": "private",
        },
    )
    assert project_resp.status_code == 200

    node_resp = api_client.post(
        "/api/v1/graph/nodes",
        json={
            "project_id": "proj-attach",
            "topic_name": "Attach Node",
            "importance": 0.6,
            "relevance": 0.6,
        },
    )
    assert node_resp.status_code == 200
    node_id = node_resp.json()["id"]

    question_resp = api_client.post(
        "/api/v1/questions",
        json={
            "id": "q-attach-1",
            "project_id": "proj-attach",
            "text": "What is attached?",
            "answer": "A material.",
            "question_type": "OPEN",
            "knowledge_type": "CONCEPT",
            "covered_node_ids": [node_id],
            "difficulty": 2,
            "tags": ["attach"],
        },
    )
    assert question_resp.status_code == 200

    material_resp = api_client.post(
        "/api/v1/materials",
        json={
            "id": "mat-attach-1",
            "project_id": "proj-attach",
            "title": "Attach Material",
            "content_text": "Attach content",
        },
    )
    assert material_resp.status_code == 200

    attach_resp = api_client.post(
        "/api/v1/materials/mat-attach-1/attach",
        json={
            "node_ids": [node_id],
            "question_ids": ["q-attach-1"],
        },
    )
    assert attach_resp.status_code == 200
    payload = attach_resp.json()
    assert payload["attached_nodes"] == 1
    assert payload["attached_questions"] == 1

    summary_resp = api_client.get(
        "/api/v1/graph",
        params={"project_id": "proj-attach"},
    )
    assert summary_resp.status_code == 200
    summary = summary_resp.json()

    material_node_id = "material:mat-attach-1"
    assert any(node["id"] == material_node_id for node in summary["nodes"])
    assert any(
        edge["source"] == material_node_id and edge["target"] == node_id
        for edge in summary["edges"]
    )


def test_material_replace_nodes(api_client):
    project_resp = api_client.post(
        "/api/v1/projects",
        json={
            "id": "proj-replace",
            "name": "Replace Project",
            "description": "Project for replace links",
            "visibility": "private",
        },
    )
    assert project_resp.status_code == 200

    node_one_resp = api_client.post(
        "/api/v1/graph/nodes",
        json={
            "project_id": "proj-replace",
            "topic_name": "First Node",
            "importance": 0.6,
            "relevance": 0.6,
        },
    )
    assert node_one_resp.status_code == 200
    node_one_id = node_one_resp.json()["id"]

    node_two_resp = api_client.post(
        "/api/v1/graph/nodes",
        json={
            "project_id": "proj-replace",
            "topic_name": "Second Node",
            "importance": 0.6,
            "relevance": 0.6,
        },
    )
    assert node_two_resp.status_code == 200
    node_two_id = node_two_resp.json()["id"]

    material_resp = api_client.post(
        "/api/v1/materials",
        json={
            "id": "mat-replace-1",
            "project_id": "proj-replace",
            "title": "Replace Material",
            "content_text": "Replace content",
        },
    )
    assert material_resp.status_code == 200

    replace_resp = api_client.put(
        "/api/v1/materials/mat-replace-1/nodes",
        json={"node_ids": [node_one_id]},
    )
    assert replace_resp.status_code == 200
    assert replace_resp.json()["node_ids"] == [node_one_id]

    replace_resp = api_client.put(
        "/api/v1/materials/mat-replace-1/nodes",
        json={"node_ids": [node_two_id]},
    )
    assert replace_resp.status_code == 200
    assert replace_resp.json()["node_ids"] == [node_two_id]

    summary_resp = api_client.get(
        "/api/v1/graph",
        params={"project_id": "proj-replace"},
    )
    assert summary_resp.status_code == 200
    summary = summary_resp.json()

    material_node_id = "material:mat-replace-1"
    edges = summary["edges"]
    assert any(
        edge["source"] == material_node_id and edge["target"] == node_two_id
        for edge in edges
    )
    assert not any(
        edge["source"] == material_node_id and edge["target"] == node_one_id
        for edge in edges
    )


def test_material_replace_nodes_creates_new(api_client):
    project_resp = api_client.post(
        "/api/v1/projects",
        json={
            "id": "proj-replace-new",
            "name": "Replace New Project",
            "description": "Project for replace links with new nodes",
            "visibility": "private",
        },
    )
    assert project_resp.status_code == 200

    material_resp = api_client.post(
        "/api/v1/materials",
        json={
            "id": "mat-replace-new-1",
            "project_id": "proj-replace-new",
            "title": "Replace Material",
            "content_text": "Replace content",
        },
    )
    assert material_resp.status_code == 200

    replace_resp = api_client.put(
        "/api/v1/materials/mat-replace-new-1/nodes",
        json={"node_ids": [], "new_nodes": [{"title": "New Suggested Node"}]},
    )
    assert replace_resp.status_code == 200
    payload = replace_resp.json()
    created_ids = payload.get("created_node_ids") or []
    assert len(created_ids) == 1

    summary_resp = api_client.get(
        "/api/v1/graph",
        params={"project_id": "proj-replace-new"},
    )
    assert summary_resp.status_code == 200
    summary = summary_resp.json()

    material_node_id = "material:mat-replace-new-1"
    edges = summary["edges"]
    assert any(
        edge["source"] == material_node_id and edge["target"] == created_ids[0]
        for edge in edges
    )


def test_material_replace_nodes_ignores_material_node_id(api_client):
    project_resp = api_client.post(
        "/api/v1/projects",
        json={
            "id": "proj-replace-invalid",
            "name": "Replace Invalid Project",
            "description": "Project for invalid node ids",
            "visibility": "private",
        },
    )
    assert project_resp.status_code == 200

    node_resp = api_client.post(
        "/api/v1/graph/nodes",
        json={
            "project_id": "proj-replace-invalid",
            "topic_name": "Valid Node",
            "importance": 0.6,
            "relevance": 0.6,
        },
    )
    assert node_resp.status_code == 200
    node_id = node_resp.json()["id"]

    material_resp = api_client.post(
        "/api/v1/materials",
        json={
            "id": "mat-replace-invalid-1",
            "project_id": "proj-replace-invalid",
            "title": "Replace Material",
            "content_text": "Replace content",
        },
    )
    assert material_resp.status_code == 200

    replace_resp = api_client.put(
        "/api/v1/materials/mat-replace-invalid-1/nodes",
        json={"node_ids": ["material:mat-replace-invalid-1", node_id]},
    )
    assert replace_resp.status_code == 200
    assert replace_resp.json()["node_ids"] == [node_id]


def test_material_replace_nodes_allows_empty(api_client):
    project_resp = api_client.post(
        "/api/v1/projects",
        json={
            "id": "proj-replace-empty",
            "name": "Replace Empty Project",
            "description": "Project for clearing material links",
            "visibility": "private",
        },
    )
    assert project_resp.status_code == 200

    node_resp = api_client.post(
        "/api/v1/graph/nodes",
        json={
            "project_id": "proj-replace-empty",
            "topic_name": "Linked Node",
            "importance": 0.6,
            "relevance": 0.6,
        },
    )
    assert node_resp.status_code == 200
    node_id = node_resp.json()["id"]

    material_resp = api_client.post(
        "/api/v1/materials",
        json={
            "id": "mat-replace-empty-1",
            "project_id": "proj-replace-empty",
            "title": "Replace Material",
            "content_text": "Replace content",
        },
    )
    assert material_resp.status_code == 200

    attach_resp = api_client.put(
        "/api/v1/materials/mat-replace-empty-1/nodes",
        json={"node_ids": [node_id]},
    )
    assert attach_resp.status_code == 200

    clear_resp = api_client.put(
        "/api/v1/materials/mat-replace-empty-1/nodes",
        json={"node_ids": []},
    )
    assert clear_resp.status_code == 200
    assert clear_resp.json()["node_ids"] == []


def test_material_suggestions_endpoint_returns_candidates(api_client, monkeypatch):
    project_resp = api_client.post(
        "/api/v1/projects",
        json={
            "id": "proj-suggest",
            "name": "Suggest Project",
            "description": "Project for suggestions",
            "visibility": "private",
        },
    )
    assert project_resp.status_code == 200

    material_resp = api_client.post(
        "/api/v1/materials",
        json={
            "id": "mat-suggest-1",
            "project_id": "proj-suggest",
            "title": "Suggest Material",
            "content_text": "Graph theory basics",
        },
    )
    assert material_resp.status_code == 200

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
        "/api/v1/materials/mat-suggest-1/suggestions",
        json={
            "project_id": "proj-suggest",
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
    assert any(item["suggestion_type"] == "NEW" for item in payload["weak"])


def test_material_suggestions_missing_project_id(api_client, monkeypatch):
    project_resp = api_client.post(
        "/api/v1/projects",
        json={
            "id": "proj-suggest-2",
            "name": "Suggest Project 2",
            "description": "Project for suggestions",
            "visibility": "private",
        },
    )
    assert project_resp.status_code == 200

    material_resp = api_client.post(
        "/api/v1/materials",
        json={
            "id": "mat-suggest-2",
            "project_id": "proj-suggest-2",
            "title": "Suggest Material",
            "content_text": "Graph theory basics",
        },
    )
    assert material_resp.status_code == 200

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
        "/api/v1/materials/mat-suggest-2/suggestions",
        json={},
    )
    assert suggest_resp.status_code == 400


def test_material_suggestions_endpoint_existing_nodes(api_client, monkeypatch):
    project_resp = api_client.post(
        "/api/v1/projects",
        json={
            "id": "proj-suggest-3",
            "name": "Suggest Project 3",
            "description": "Project for suggestions",
            "visibility": "private",
        },
    )
    assert project_resp.status_code == 200

    node_resp = api_client.post(
        "/api/v1/graph/nodes",
        json={
            "project_id": "proj-suggest-3",
            "topic_name": "Graph Basics",
            "importance": 0.6,
            "relevance": 0.6,
        },
    )
    assert node_resp.status_code == 200
    node_id = node_resp.json()["id"]

    material_resp = api_client.post(
        "/api/v1/materials",
        json={
            "id": "mat-suggest-3",
            "project_id": "proj-suggest-3",
            "title": "Suggest Material",
            "content_text": "Graph theory basics",
        },
    )
    assert material_resp.status_code == 200

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
        "app.api.materials.PostgresNodeSuggestionRepository",
        FakeRepo,
    )

    suggest_resp = api_client.post(
        "/api/v1/materials/mat-suggest-3/suggestions",
        json={
            "project_id": "proj-suggest-3",
            "threshold": 0.75,
            "semantic_weight": 0.6,
            "keyword_weight": 0.4,
            "top_k": 20,
        },
    )
    assert suggest_resp.status_code == 200
    payload = suggest_resp.json()
    assert any(item["node_id"] == node_id for item in payload["strong"])
