"""API tests for user endpoint."""


def test_get_current_user(api_client):
    resp = api_client.get("/api/v1/users/me")
    assert resp.status_code == 200
    data = resp.json()
    assert data["username"] == "admin"
    assert data["id"] == "admin"
