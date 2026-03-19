"""Local document parsing helpers for research tasks."""
from __future__ import annotations

from base64 import b64decode
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from typing import Any

try:
    from pypdf import PdfReader
except Exception:  # pragma: no cover - optional dependency
    PdfReader = None


_TEXT_EXTENSIONS = {".txt", ".md", ".markdown"}
_TEXT_MIME_TYPES = {"text/plain", "text/markdown"}
_PDF_EXTENSIONS = {".pdf"}
_PDF_MIME_TYPES = {"application/pdf"}
_MAX_TEXT_CHARS = 12000


def _decode_document_content(content_base64: str) -> bytes:
    """Decode base64-encoded document content."""
    try:
        return b64decode(content_base64, validate=True)
    except Exception as exc:  # pragma: no cover - defensive path
        raise ValueError("Uploaded document content is invalid") from exc


def _extract_pdf_text(filename: str, content: bytes) -> str:
    """Extract readable text from a PDF payload."""
    if PdfReader is None:
        raise ValueError("PDF parsing is unavailable because pypdf is not installed")

    try:
        reader = PdfReader(BytesIO(content))
        text = "\n".join((page.extract_text() or "").strip() for page in reader.pages)
    except Exception as exc:  # pragma: no cover - parser failure path
        raise ValueError(f"Failed to parse uploaded PDF: {filename}") from exc

    normalized_text = text.strip()
    if not normalized_text:
        raise ValueError("Uploaded document does not contain readable text")
    return normalized_text


def parse_research_document(
    *,
    filename: str,
    content_base64: str,
    mime_type: str | None = None,
) -> dict[str, Any]:
    """Parse a user-provided document into normalized research context."""
    normalized_name = filename.strip()
    if not normalized_name:
        raise ValueError("Uploaded document filename is required")

    suffix = Path(normalized_name).suffix.lower()
    content = _decode_document_content(content_base64)
    if not content:
        raise ValueError("Uploaded document is empty")

    normalized_mime = (mime_type or "").strip().lower()
    if suffix in _PDF_EXTENSIONS or normalized_mime in _PDF_MIME_TYPES:
        text = _extract_pdf_text(normalized_name, content)
        source_type = "local_pdf"
    elif suffix in _TEXT_EXTENSIONS or normalized_mime in _TEXT_MIME_TYPES or not suffix:
        try:
            text = content.decode("utf-8").strip()
        except UnicodeDecodeError as exc:
            raise ValueError("Uploaded text document must be UTF-8 encoded") from exc
        if not text:
            raise ValueError("Uploaded document does not contain readable text")
        source_type = "local_document"
    else:
        raise ValueError("Unsupported document type. Please upload TXT, MD, or PDF")

    return {
        "filename": normalized_name,
        "mime_type": normalized_mime or None,
        "source_type": source_type,
        "text": text[:_MAX_TEXT_CHARS],
    }


def build_document_source(document: dict[str, Any]) -> dict[str, Any]:
    """Convert parsed document text into a normalized research source."""
    text = document["text"].strip()
    preview = text[:1200]
    published_at = datetime.now(UTC).isoformat()
    filename = document["filename"]

    return {
        "source_id": "local-document-1",
        "title": filename,
        "authors": [],
        "abstract": preview,
        "published_at": published_at,
        "url": f"local://{filename}",
        "pdf_url": None,
        "primary_category": "uploaded-document",
        "categories": ["uploaded-document"],
        "comment": None,
        "journal_ref": None,
        "doi": None,
        "citation_text": f"{filename}. Uploaded local document.",
        "source_type": document["source_type"],
        "score": 100,
        "document_text": text,
        "document_filename": filename,
        "mime_type": document.get("mime_type"),
    }
