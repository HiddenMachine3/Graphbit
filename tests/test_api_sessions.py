"""API tests for default sessions."""


def test_default_session_uses_admin(api_client):
    response = api_client.get("/api/v1/sessions/current")
    assert response.status_code == 200
    payload = response.json()
    assert payload["user_id"] == "admin"
