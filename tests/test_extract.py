from io import BytesIO
from types import SimpleNamespace

from PIL import Image
import pytest
from pypdf import PdfWriter

from app.extract import ExtractionError, extract_text


def make_pdf():
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def test_pdf_without_text_layer_fails_clearly():
    with pytest.raises(ExtractionError, match="Aucun texte détecté"):
        extract_text(make_pdf(), "application/pdf", "fr")


def test_native_pdf_uses_pdf_parser(monkeypatch):
    page = SimpleNamespace(extract_text=lambda: "Texte du PDF")
    monkeypatch.setattr(
        "app.extract.PdfReader",
        lambda *args, **kwargs: SimpleNamespace(pages=[page]),
    )
    text, method = extract_text(b"pdf", "application/pdf", "fr")
    assert (text, method) == ("Texte du PDF", "pdf_parser")


def test_image_is_routed_to_ocr(monkeypatch):
    image = Image.new("RGB", (4, 4), color="white")
    encoded = BytesIO()
    image.save(encoded, format="PNG")
    calls = {}

    def fake_ocr(received_image, lang, config):
        calls["lang"] = lang
        calls["config"] = config
        assert received_image.size == (16, 16)
        return "Texte OCR"

    monkeypatch.setattr("app.extract.pytesseract.image_to_string", fake_ocr)
    text, method = extract_text(encoded.getvalue(), "image/png", "fr")
    assert (text, method) == ("Texte OCR", "ocr")
    assert calls["lang"] == "fra+eng"
    assert calls["config"] == "--oem 1 --psm 6"


def test_rejects_unavailable_language():
    with pytest.raises(ValueError, match="Langue OCR"):
        extract_text(b"image", "image/png", "de")
