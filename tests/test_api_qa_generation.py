"""Single test case for QA generation endpoint."""


def test_generate_qa_pairs_success(api_client):
    response = api_client.post(
        "/api/v1/qa/generate",
        json={
            "text": "Photosynthesis is the process by which plants convert sunlight into chemical energy.",
            "n": 3,
        },
    )




    assert response.status_code == 200
    payload = response.json()
    
    print(payload["qa_pairs"])
    assert "qa_pairs" in payload
    assert isinstance(payload["qa_pairs"], list)
    assert len(payload["qa_pairs"]) == 3
    assert all("question" in pair and "answer" in pair for pair in payload["qa_pairs"])