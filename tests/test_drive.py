import pytest
import requests

from app.drive import DriveError, extract_folder_id, list_public_files


def test_extract_folder_id_from_standard_link():
    assert extract_folder_id("https://drive.google.com/drive/folders/abc_123") == "abc_123"


@pytest.mark.parametrize(
    "url",
    [
        "http://drive.google.com/drive/folders/abc",
        "https://example.com/drive/folders/abc",
        "https://drive.google.com/drive/folders/",
        "https://drive.google.com/drive/folders/invalid!",
    ],
)
def test_rejects_invalid_or_untrusted_folder_links(url):
    with pytest.raises(ValueError):
        extract_folder_id(url)


def test_list_public_files_filters_unsupported_mime_types(monkeypatch):
    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {
                "files": [
                    {"id": "pdf_1", "name": "report.pdf", "mimeType": "application/pdf", "size": "123"},
                    {"id": "img_1", "name": "photo.jpg", "mimeType": "image/jpeg"},
                    {"id": "doc_1", "name": "notes.docx", "mimeType": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
                ]
            }

    monkeypatch.setattr("app.drive.requests.get", lambda *args, **kwargs: Response())
    files = list_public_files("https://drive.google.com/drive/folders/folder_1", "test-key")
    assert [file["id"] for file in files] == ["pdf_1", "img_1"]
    assert files[0]["size"] == 123
    assert files[1]["size"] is None


def test_private_folder_error_is_clear(monkeypatch):
    class Response:
        def raise_for_status(self):
            raise requests.HTTPError(
                "forbidden",
                response=type("ErrorResponse", (), {"status_code": 403})(),
            )

    monkeypatch.setattr("app.drive.requests.get", lambda *args, **kwargs: Response())
    with pytest.raises(DriveError, match="partage public"):
        list_public_files("https://drive.google.com/drive/folders/folder_1", "test-key")
