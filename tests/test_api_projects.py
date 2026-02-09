"""API tests for project CRUD."""


def test_project_crud(api_client):
    create_resp = api_client.post(
        "/api/v1/projects",
        json={
            "id": "proj-1",
            "name": "Project One",
            "description": "First project",
            "visibility": "public",
        },
    )
    assert create_resp.status_code == 200
    created = create_resp.json()
    assert created["id"] == "proj-1"
    assert created["owner_id"] == "admin"

    list_resp = api_client.get("/api/v1/projects")
    assert list_resp.status_code == 200
    ids = {project["id"] for project in list_resp.json()}
    assert "proj-1" in ids

    get_resp = api_client.get("/api/v1/projects/proj-1")
    assert get_resp.status_code == 200
    assert get_resp.json()["name"] == "Project One"

    update_resp = api_client.patch(
        "/api/v1/projects/proj-1",
        json={"name": "Project Uno"},
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["name"] == "Project Uno"

    delete_resp = api_client.delete("/api/v1/projects/proj-1")
    assert delete_resp.status_code == 200

    missing_resp = api_client.get("/api/v1/projects/proj-1")
    assert missing_resp.status_code == 404
