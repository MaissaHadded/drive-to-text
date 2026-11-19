from io import BytesIO

from PIL import Image, UnidentifiedImageError
from pypdf import PdfReader
import pytesseract
from pytesseract import TesseractNotFoundError


OCR_LANGUAGES = {"fr": "fra", "en": "eng", "ar": "ara"}


class ExtractionError(Exception):
    pass


def extract_text(content: bytes, mime_type: str, ocr_language: str) -> tuple[str, str]:
    if ocr_language not in OCR_LANGUAGES:
        raise ValueError("Langue OCR non prise en charge.")

    if mime_type == "application/pdf":
        try:
            reader = PdfReader(BytesIO(content), strict=True)
            text = "\n\n".join(page.extract_text() or "" for page in reader.pages).strip()
        except Exception as exc:
            raise ExtractionError("Le PDF est illisible ou endommagé.") from exc
        if not text:
            raise ExtractionError(
                "Aucun texte détecté. L’OCR des PDF scannés n’est pas pris en charge."
            )
        return text, "pdf_parser"

    if mime_type in {"image/png", "image/jpeg"}:
        try:
            with Image.open(BytesIO(content)) as image:
                image.load()
                text = pytesseract.image_to_string(
                    image,
                    lang=OCR_LANGUAGES[ocr_language],
                ).strip()
        except TesseractNotFoundError as exc:
            raise ExtractionError(
                "Tesseract est absent. Installez-le ou lancez l’application avec Docker."
            ) from exc
        except pytesseract.TesseractError as exc:
            raise ExtractionError(
                f"Échec OCR : vérifiez que la langue {ocr_language} est installée."
            ) from exc
        except (UnidentifiedImageError, OSError) as exc:
            raise ExtractionError("L’image est illisible ou dans un format non pris en charge.") from exc
        return text, "ocr"

    raise ExtractionError("Type de fichier non pris en charge.")
