"""Ingestion orchestration: validate, parse, normalize one uploaded file."""

from __future__ import annotations

import hashlib
import os

from app.core.constants import FILE_TYPE_LABEL, UNSAFE_FILENAME_CHARS
from app.core.exceptions import DuplicateDocumentError
from app.core.logging import get_logger
from app.models.domain import DocumentMeta, ExtractedPage, new_id
from app.services.ingestion.parsers import parse_by_extension
from app.services.ingestion.validation import validate_upload

logger = get_logger("sourcelens.ingestion")


def sanitize_filename(name: str, max_len: int = 120) -> str:
    base = os.path.basename(name)
    # Strip directory components and unsafe characters.
    cleaned = base
    for ch in UNSAFE_FILENAME_CHARS:
        cleaned = cleaned.replace(ch, "_")
    cleaned = cleaned.strip().strip("._").strip()
    if not cleaned:
        cleaned = "document"
    if len(cleaned) > max_len:
        stem, ext = os.path.splitext(cleaned)
        cleaned = stem[: max_len - len(ext) - 1] + "_" + ext
    return cleaned


def content_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def ingest_file(
    filename: str,
    data: bytes,
    *,
    max_bytes: int,
    seen_hashes: set[str] | None = None,
) -> tuple[DocumentMeta, list[ExtractedPage]]:
    """Validate and parse a single upload into metadata + extracted pages."""
    ext = validate_upload(filename, len(data), max_bytes)
    safe_name = sanitize_filename(filename)
    file_hash = content_hash(data)

    if seen_hashes is not None and file_hash in seen_hashes:
        raise DuplicateDocumentError(
            f"'{safe_name}' appears to be a duplicate of an already uploaded file."
        )

    document_id = new_id("doc")
    pages = parse_by_extension(data, filename=safe_name, document_id=document_id, ext=ext)

    meta = DocumentMeta(
        document_id=document_id,
        filename=safe_name,
        original_filename=filename,
        mime_type=_mime_for(ext),
        size_bytes=len(data),
        content_hash=file_hash,
        status="indexed",
    )
    logger.info(
        "ingestion.parsed",
        extra={"sl_document_id": document_id, "sl_pages": len(pages), "sl_ext": ext},
    )
    return meta, pages


def _mime_for(ext: str) -> str:
    return {
        ".pdf": "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".txt": "text/plain",
        ".md": "text/markdown",
    }.get(ext, "application/octet-stream")
