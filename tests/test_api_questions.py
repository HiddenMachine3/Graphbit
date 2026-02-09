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
