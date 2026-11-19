import re
from urllib.parse import parse_qs, urlparse

import requests


DRIVE_API_URL = "https://www.googleapis.com/drive/v3/files"
SUPPORTED_MIME_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
}
FILE_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,200}$")


class DriveError(Exception):
    pass


def extract_folder_id(folder_url: str) -> str:
    try:
        parsed = urlparse(folder_url)
    except ValueError as exc:
        raise ValueError("URL Google Drive invalide.") from exc

    if parsed.scheme != "https" or parsed.hostname not in {
        "drive.google.com",
        "www.drive.google.com",
    }:
        raise ValueError("Fournissez un lien HTTPS vers un dossier Google Drive.")

    path_parts = [part for part in parsed.path.split("/") if part]
    folder_id = None
    if len(path_parts) >= 3 and path_parts[:2] == ["drive", "folders"]:
        folder_id = path_parts[2]
    elif "id" in parse_qs(parsed.query):
        folder_id = parse_qs(parsed.query)["id"][0]

    if not folder_id or not FILE_ID_PATTERN.fullmatch(folder_id):
        raise ValueError("Le lien ne contient pas d’identifiant de dossier valide.")
    return folder_id


def list_public_files(folder_url: str, api_key: str) -> list[dict]:
    folder_id = extract_folder_id(folder_url)
    files = []
    page_token = None

    while True:
        params = {
            "key": api_key,
            "q": f"'{folder_id}' in parents and trashed = false",
            "pageSize": 1000,
            "fields": "nextPageToken,files(id,name,mimeType,size)",
            "orderBy": "name",
        }
        if page_token:
            params["pageToken"] = page_token

        try:
            response = requests.get(DRIVE_API_URL, params=params, timeout=20)
            response.raise_for_status()
            payload = response.json()
        except requests.RequestException as exc:
            status_code = getattr(exc.response, "status_code", None)
            if status_code in {403, 404}:
                raise DriveError(
                    "Dossier introuvable ou inaccessible. Vérifiez le lien, le partage public "
                    "et la configuration de la clé API."
                ) from exc
            raise DriveError("Google Drive n’a pas pu être contacté.") from exc
        except ValueError as exc:
            raise DriveError("Google Drive a renvoyé une réponse invalide.") from exc

        for item in payload.get("files", []):
            mime_type = item.get("mimeType")
            file_id = item.get("id")
            if (
                mime_type in SUPPORTED_MIME_TYPES
                and isinstance(file_id, str)
                and FILE_ID_PATTERN.fullmatch(file_id)
            ):
                files.append(
                    {
                        "id": file_id,
                        "name": item.get("name") or file_id,
                        "mime_type": mime_type,
                        "size": int(item["size"])
                        if isinstance(item.get("size"), str) and item["size"].isdigit()
                        else None,
                    }
                )

        page_token = payload.get("nextPageToken")
        if not page_token:
            return files


def download_public_file(file_id: str, api_key: str, max_bytes: int) -> bytes:
    if not FILE_ID_PATTERN.fullmatch(file_id):
        raise ValueError("Identifiant de fichier invalide.")

    try:
        with requests.get(
            f"{DRIVE_API_URL}/{file_id}",
            params={"key": api_key, "alt": "media"},
            stream=True,
            timeout=(10, 30),
        ) as response:
            response.raise_for_status()
            content_length = response.headers.get("Content-Length")
            if content_length and int(content_length) > max_bytes:
                raise DriveError("Le fichier dépasse la taille maximale autorisée.")

            chunks = []
            total = 0
            for chunk in response.iter_content(chunk_size=64 * 1024):
                if not chunk:
                    continue
                total += len(chunk)
                if total > max_bytes:
                    raise DriveError("Le fichier dépasse la taille maximale autorisée.")
                chunks.append(chunk)
            return b"".join(chunks)
    except DriveError:
        raise
    except requests.RequestException as exc:
        status_code = getattr(exc.response, "status_code", None)
        if status_code in {403, 404}:
            raise DriveError(
                "Fichier introuvable ou inaccessible publiquement dans Google Drive."
            ) from exc
        raise DriveError("Le fichier n’a pas pu être téléchargé depuis Google Drive.") from exc
