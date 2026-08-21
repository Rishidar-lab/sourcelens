"""Shared constants for the ingestion and RAG pipeline."""

from __future__ import annotations

ACCEPTED_EXTENSIONS: tuple[str, ...] = (".pdf", ".docx", ".txt", ".md")

# MIME types we accept / expect. Used as a secondary validation signal only;
# we never trust the client-declared MIME as proof of safety.
EXPECTED_MIME: dict[str, tuple[str, ...]] = {
    ".pdf": ("application/pdf",),
    ".docx": (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ),
    ".txt": ("text/plain",),
    ".md": ("text/markdown", "text/plain"),
}

# Map file extension -> human readable type shown in the UI.
FILE_TYPE_LABEL: dict[str, str] = {
    ".pdf": "PDF",
    ".docx": "DOCX",
    ".txt": "TXT",
    ".md": "Markdown",
}

# A sentinel used when a chunk has no resolvable page number.
UNKNOWN_PAGE = -1

# Chroma collection names. Keeping them explicit avoids accidental clashes.
CHUNKS_COLLECTION = "sourcelens_chunks"
DOCUMENTS_COLLECTION = "sourcelens_documents"

# Reserved characters stripped from uploaded filenames. Note: "." is kept so
# file extensions (e.g. ".pdf") survive; path components are removed via
# os.path.basename before this runs.
UNSAFE_FILENAME_CHARS = "/\\;&|<>$\"`*?:"


class IngestionStatus:
    PENDING = "pending"
    UPLOADING = "uploading"
    EXTRACTING = "extracting"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    INDEXED = "indexed"
    FAILED = "failed"
