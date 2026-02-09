"""API tests for community CRUD and activation."""


def test_community_crud(api_client):
    create_resp = api_client.post(
        "/api/v1/communities",
        json={
            "id": "comm-1",
            "name": "Community One",
            "description": "Testing community",
            "project_ids": ["proj-1"],
            "member_ids": ["admin"],
            "node_importance_overrides": {"proj-1": {"node-a": 1.2}},
        },
    )
    assert create_resp.status_code == 200

    list_resp = api_client.get("/api/v1/communities")
    assert list_resp.status_code == 200
    ids = {community["id"] for community in list_resp.json()}
    assert "comm-1" in ids

    get_resp = api_client.get("/api/v1/communities/comm-1")
    assert get_resp.status_code == 200
    assert get_resp.json()["name"] == "Community One"

    update_resp = api_client.patch(
        "/api/v1/communities/comm-1",
        json={"description": "Updated"},
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["description"] == "Updated"

    activate_resp = api_client.post(
        "/api/v1/communities/active",
        json={"community_id": "comm-1"},
    )
    assert activate_resp.status_code == 200

    delete_resp = api_client.delete("/api/v1/communities/comm-1")
    assert delete_resp.status_code == 200

    missing_resp = api_client.get("/api/v1/communities/comm-1")
    assert missing_resp.status_code == 404
