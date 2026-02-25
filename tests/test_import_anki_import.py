"""Integration test for importing the provided Amino Acid Anki package."""

from pathlib import Path


ANKI_FILE_PATH = Path(__file__).resolve().parents[1] / "data" / "Amino_Acid_Flashcards.apkg"


def test_import_anki_package(api_client):
    assert ANKI_FILE_PATH.exists(), f"Anki file not found: {ANKI_FILE_PATH}"

    project_response = api_client.post(
        "/api/v1/projects",
        json={
            "id": "proj-import-amino-anki",
            "name": "Amino Anki Import Project",
            "description": "Project for testing Anki import",
            "visibility": "private",
        },
    )
    assert project_response.status_code == 200

    with ANKI_FILE_PATH.open("rb") as handle:
        preview_response = api_client.post(
            "/api/v1/questions/import/preview",
            files={"file": (ANKI_FILE_PATH.name, handle, "application/octet-stream")},
        )

    assert preview_response.status_code == 200, preview_response.text
    preview_payload = preview_response.json()
    assert preview_payload["total_count"] > 0
    assert len(preview_payload["questions"]) > 0

    with ANKI_FILE_PATH.open("rb") as handle:
        import_response = api_client.post(
            "/api/v1/questions/import",
            data={"project_id": "proj-import-amino-anki"},
            files={"file": (ANKI_FILE_PATH.name, handle, "application/octet-stream")},
        )

    assert import_response.status_code == 200, import_response.text
    import_payload = import_response.json()
    assert import_payload["imported_count"] > 0

    list_response = api_client.get(
        "/api/v1/questions",
        params={"project_id": "proj-import-amino-anki"},
    )
    assert list_response.status_code == 200
    assert len(list_response.json()) == import_payload["imported_count"]
