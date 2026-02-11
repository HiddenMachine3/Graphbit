"""API tests for graph summary material linking."""


def test_graph_summary_includes_material_nodes(api_client):
    project_resp = api_client.post(
        "/api/v1/projects",
        json={
            "id": "proj-g",
            "name": "Graph Project",
            "description": "Project for graph summary",
            "visibility": "private",
        },
    )
    assert project_resp.status_code == 200

    node_resp = api_client.post(
        "/api/v1/graph/nodes",
        json={
            "project_id": "proj-g",
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
            "id": "mat-graph-1",
            "project_id": "proj-g",
            "title": "Graph Materials",
            "content_text": "Intro to graphs.\n\nEdges and nodes.",
        },
    )
    assert material_resp.status_code == 200
    material_id = material_resp.json()["id"]

    question_resp = api_client.post(
        "/api/v1/questions",
        json={
            "id": "q-graph-1",
            "project_id": "proj-g",
            "text": "What is a graph?",
            "answer": "A set of nodes connected by edges.",
            "question_type": "OPEN",
            "knowledge_type": "CONCEPT",
            "covered_node_ids": [node_id],
            "difficulty": 2,
            "tags": ["graphs"],
            "source_material_ids": [material_id],
        },
    )
    assert question_resp.status_code == 200

    summary_resp = api_client.get("/api/v1/graph", params={"project_id": "proj-g"})
    assert summary_resp.status_code == 200
    summary = summary_resp.json()

    material_node_id = f"material:{material_id}"
    assert any(node["id"] == material_node_id for node in summary["nodes"])
    assert any(
        edge["source"] == material_node_id and edge["target"] == node_id
        for edge in summary["edges"]
    )
