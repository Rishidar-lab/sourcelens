"""Document parsers for the supported file types.

Each parser returns a list of :class:`ExtractedPage`. PDFs keep a real page
number; DOCX/TXT/MD do not have pages, so ``page`` is left as the unknown
sentinel and the chunker preserves that for citations.
"""

from __future__ import annotations

import io

from app.core.constants import UNKNOWN_PAGE
from app.core.exceptions import CorruptDocumentError, EmptyDocumentError
from app.core.logging import get_logger
from app.models.domain import ExtractedPage

logger = get_logger("sourcelens.ingestion")


def _decode_text(raw: bytes) -> str:
    for enc in ("utf-8", "utf-8-sig", "latin-1", "cp1252"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    # Last resort: replace invalid bytes. We never want to crash on encoding.
    return raw.decode("utf-8", errors="replace")


def parse_pdf(data: bytes, *, filename: str, document_id: str) -> list[ExtractedPage]:
    try:
        import fitz  # PyMuPDF
    except ImportError as exc:  # pragma: no cover
        raise CorruptDocumentError("PDF parsing is unavailable (PyMuPDF missing).") from exc

    try:
        doc = fitz.open(stream=data, filetype="pdf")
    except Exception as exc:  # noqa: BLE001
        raise CorruptDocumentError(f"Could not read PDF '{filename}': {exc}") from exc

    pages: list[ExtractedPage] = []
    try:
        if doc.page_count == 0:
            raise CorruptDocumentError(f"PDF '{filename}' contains no pages.")
        for i in range(doc.page_count):
            page = doc.load_page(i)
            text = page.get_text("text")
            pages.append(
                ExtractedPage(
                    document_id=document_id,
                    filename=filename,
                    page=i + 1,
                    text=text or "",
                )
            )
    finally:
        doc.close()

    total = sum(len(p.text.strip()) for p in pages)
    if total == 0:
        raise EmptyDocumentError(
            f"PDF '{filename}' produced no extractable text (it may be scanned/image-based)."
        )
    return pages


def parse_docx(data: bytes, *, filename: str, document_id: str) -> list[ExtractedPage]:
    try:
        from docx import Document
    except ImportError as exc:  # pragma: no cover
        raise CorruptDocumentError("DOCX parsing is unavailable (python-docx missing).") from exc

    try:
        doc = Document(io.BytesIO(data))
    except Exception as exc:  # noqa: BLE001
        raise CorruptDocumentError(f"Could not read DOCX '{filename}': {exc}") from exc

    parts: list[str] = []
    for para in doc.paragraphs:
        text = para.text.strip()
        if text:
            parts.append(text)
    joined = "\n".join(parts)
    if not joined.strip():
        raise EmptyDocumentError(f"DOCX '{filename}' contains no extractable text.")
    return [
        ExtractedPage(
            document_id=document_id,
            filename=filename,
            page=UNKNOWN_PAGE,
            text=joined,
        )
    ]


def parse_text(
    data: bytes, *, filename: str, document_id: str, is_markdown: bool = False
) -> list[ExtractedPage]:
    text = _decode_text(data)
    if not text.strip():
        raise EmptyDocumentError(f"File '{filename}' is empty.")
    return [
        ExtractedPage(
            document_id=document_id,
            filename=filename,
            page=UNKNOWN_PAGE,
            text=text,
        )
    ]


def parse_by_extension(
    data: bytes, *, filename: str, document_id: str, ext: str
) -> list[ExtractedPage]:
    ext = ext.lower()
    if ext == ".pdf":
        return parse_pdf(data, filename=filename, document_id=document_id)
    if ext == ".docx":
        return parse_docx(data, filename=filename, document_id=document_id)
    if ext in (".txt", ".md"):
        return parse_text(
            data, filename=filename, document_id=document_id, is_markdown=ext == ".md"
        )
    raise UnsupportedFileTypeError(f"Unsupported extension '{ext}'.")
