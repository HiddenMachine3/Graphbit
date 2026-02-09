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
