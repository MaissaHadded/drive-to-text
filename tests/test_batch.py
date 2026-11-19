import time

from fastapi.testclient import TestClient

from app import main
from app.extract import ExtractionError


def test_batch_keeps_processing_after_a_file_fails(monkeypatch):
    monkeypatch.setenv("GOOGLE_DRIVE_API_KEY", "test-key")
    monkeypatch.setenv("MAX_FILE_SIZE_MB", "1")
    files = [
        {"id": "good", "name": "good.pdf", "mime_type": "application/pdf", "size": 1},
        {"id": "bad", "name": "bad.pdf", "mime_type": "application/pdf", "size": 1},
    ]
    monkeypatch.setattr(main, "list_public_files", lambda *args: files)
    monkeypatch.setattr(main, "download_public_file", lambda file_id, *_: file_id.encode())

    def extract(content, *_):
        if content == b"bad":
            raise ExtractionError("PDF illisible.")
        return "Texte extrait", "pdf_parser"

    monkeypatch.setattr(main, "extract_text", extract)

    with TestClient(main.app) as client:
        response = client.post(
            "/api/batches",
            json={
                "folder_url": "https://drive.google.com/drive/folders/folder",
                "file_ids": ["good", "bad"],
                "ocr_language": "fr",
            },
        )
        assert response.status_code == 202
        batch_id = response.json()["batch_id"]
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            batch = client.get(f"/api/batches/{batch_id}").json()
            if batch["status"] == "done":
                break
            time.sleep(0.01)

    assert batch["status"] == "done"
    assert [file["status"] for file in batch["files"]] == ["done", "failed"]
    assert batch["files"][0]["text"] == "Texte extrait"
    assert batch["files"][1]["error"] == "PDF illisible."
