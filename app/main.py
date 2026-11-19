import asyncio
import logging
import os
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.drive import DriveError, download_public_file, list_public_files
from app.extract import ExtractionError, OCR_LANGUAGES, extract_text


load_dotenv()
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)
STATIC_DIR = Path(__file__).parent / "static"
ALLOWED_OCR_LANGUAGES = set(OCR_LANGUAGES)


class DriveFolderRequest(BaseModel):
    folder_url: str = Field(min_length=1, max_length=2048)


class BatchRequest(DriveFolderRequest):
    file_ids: list[str] = Field(min_length=1, max_length=100)
    ocr_language: str = "fr"


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.batches = {}
    yield


app = FastAPI(title="Drive-to-Text", version="1.0.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def get_api_key() -> str:
    api_key = os.getenv("GOOGLE_DRIVE_API_KEY", "").strip()
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="Configurez GOOGLE_DRIVE_API_KEY dans votre fichier .env.",
        )
    return api_key


def get_max_file_bytes() -> int:
    try:
        max_size_mb = int(os.getenv("MAX_FILE_SIZE_MB", "20"))
    except ValueError as exc:
        raise HTTPException(
            status_code=500,
            detail="MAX_FILE_SIZE_MB doit être un nombre entier positif.",
        ) from exc
    if max_size_mb <= 0:
        raise HTTPException(
            status_code=500,
            detail="MAX_FILE_SIZE_MB doit être un nombre entier positif.",
        )
    return max_size_mb * 1024 * 1024


@app.get("/")
async def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.post("/api/drive/files")
async def get_drive_files(request: DriveFolderRequest):
    api_key = get_api_key()
    try:
        files = await asyncio.to_thread(list_public_files, request.folder_url, api_key)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except DriveError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {"files": files}


async def process_file(file: dict, api_key: str, max_bytes: int, ocr_language: str):
    file.update(status="processing", text=None, method=None, error=None)
    try:
        content = await asyncio.to_thread(
            download_public_file,
            file["id"],
            api_key,
            max_bytes,
        )
        text, method = await asyncio.to_thread(
            extract_text,
            content,
            file["mime_type"],
            ocr_language,
        )
        file.update(status="done", text=text, method=method)
    except Exception as exc:
        logger.error("Échec du traitement du fichier %s : %s", file["id"], exc)
        file.update(status="failed", error=str(exc))


async def run_batch(batch: dict, api_key: str, max_bytes: int, ocr_language: str):
    semaphore = asyncio.Semaphore(3)

    async def process_limited(file: dict):
        async with semaphore:
            await process_file(file, api_key, max_bytes, ocr_language)

    await asyncio.gather(*(process_limited(file) for file in batch["files"]))
    batch["status"] = "done"


@app.post("/api/batches", status_code=202)
async def create_batch(request: BatchRequest):
    if request.ocr_language not in ALLOWED_OCR_LANGUAGES:
        raise HTTPException(status_code=400, detail="Langue OCR non prise en charge.")

    api_key = get_api_key()
    try:
        available_files = await asyncio.to_thread(
            list_public_files,
            request.folder_url,
            api_key,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except DriveError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    requested_ids = set(request.file_ids)
    if len(requested_ids) != len(request.file_ids):
        raise HTTPException(status_code=400, detail="La sélection contient des doublons.")
    files_by_id = {file["id"]: file for file in available_files}
    if not requested_ids.issubset(files_by_id):
        raise HTTPException(
            status_code=400,
            detail="La sélection contient des fichiers absents du dossier ou non pris en charge.",
        )

    max_bytes = get_max_file_bytes()

    batch_id = str(uuid.uuid4())
    batch = {
        "id": batch_id,
        "status": "processing",
        "files": [
            {
                **files_by_id[file_id],
                "status": "pending",
                "text": None,
                "method": None,
                "error": None,
            }
            for file_id in request.file_ids
        ],
    }
    app.state.batches[batch_id] = batch
    asyncio.create_task(run_batch(batch, api_key, max_bytes, request.ocr_language))
    return {"batch_id": batch_id, "status": batch["status"]}


@app.get("/api/batches/{batch_id}")
async def get_batch(batch_id: str):
    batch = app.state.batches.get(batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail="Lot introuvable.")
    return batch


@app.get("/api/health")
async def health():
    return {"status": "ok"}
