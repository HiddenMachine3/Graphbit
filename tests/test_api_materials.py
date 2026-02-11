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
