"""Internal domain models used by the services (not the public API surface)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


class ExtractedPage(BaseModel):
    """One extracted page / logical block from a source document."""

    document_id: str
    filename: str
    page: int = -1
    text: str


class DocumentMeta(BaseModel):
    """Metadata describing one ingested document."""

    document_id: str
    filename: str
    original_filename: str
    mime_type: str
    size_bytes: int
    content_hash: str
    chunk_count: int = 0
    status: str = "indexed"
    created_at: str = Field(default_factory=_now)
    error: Optional[str] = None


class Chunk(BaseModel):
    """A chunk of text plus the source metadata required for citations."""

    chunk_id: str
    document_id: str
    filename: str
    page: int = -1
    chunk_index: int
    text: str


class RetrievedEvidence(BaseModel):
    """A retrieved chunk enriched with its relevance score."""

    chunk_id: str
    document_id: str
    filename: str
    page: int
    chunk_index: int
    score: float
    text: str
    document: str = ""  # filled with `text` for convenience downstream

    @property
    def excerpt(self) -> str:
        return self.text
