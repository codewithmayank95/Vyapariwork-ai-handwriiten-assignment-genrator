from __future__ import annotations

import io
import re

from fastapi import UploadFile


class TextExtractionError(ValueError):
    pass


_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
_SPACE_RUN = re.compile(r"[ \t]+")
_BLANK_RUN = re.compile(r"\n{3,}")


def clean_text(text: str | None) -> str:
    if not text:
        return ""
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    normalized = _CONTROL_CHARS.sub("", normalized)
    normalized = "\n".join(_SPACE_RUN.sub(" ", line).strip() for line in normalized.split("\n"))
    normalized = _BLANK_RUN.sub("\n\n", normalized)
    return normalized.strip()


async def extract_text_from_upload(upload: UploadFile, max_upload_bytes: int) -> str:
    filename = upload.filename or ""
    content_type = upload.content_type or ""
    if not filename.lower().endswith(".pdf") and content_type != "application/pdf":
        raise TextExtractionError("Please upload a valid PDF file.")

    data = await upload.read()
    if not data:
        raise TextExtractionError("Uploaded PDF is empty.")
    if len(data) > max_upload_bytes:
        raise TextExtractionError("PDF is too large for this server.")

    text = _extract_with_pymupdf(data) or _extract_with_pdfplumber(data)
    cleaned = clean_text(text)
    if not cleaned:
        raise TextExtractionError("No readable text was found in the PDF.")
    return cleaned


def _extract_with_pymupdf(data: bytes) -> str:
    try:
        import fitz
    except Exception:
        return ""

    try:
        document = fitz.open(stream=data, filetype="pdf")
    except Exception as exc:
        raise TextExtractionError(f"Could not open PDF: {exc}") from exc

    try:
        pages = [page.get_text("text") for page in document]
        return "\n\n".join(page for page in pages if page.strip())
    finally:
        document.close()


def _extract_with_pdfplumber(data: bytes) -> str:
    try:
        import pdfplumber
    except Exception:
        return ""

    try:
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            pages = [(page.extract_text() or "") for page in pdf.pages]
    except Exception:
        return ""
    return "\n\n".join(page for page in pages if page.strip())
