"""Single test case for QA generation endpoint."""


def test_generate_qa_pairs_success(api_client):
    response = api_client.post(
        "/api/v1/qa/generate",
        json={
            "text": "hello friends I'm going to start a course on algorithms and whoever messes up cake algorithm is a common subject for computer science engineering students most of the universities offer this course as a part of syllabus and this is a very cool subject and very important subject and students face some difficulties in some of the topics in this one they could not understand them",
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