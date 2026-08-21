"""Pydantic schemas for the public REST API."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, field_validator


class ErrorResponse(BaseModel):
    error: dict


# --- Health & config -------------------------------------------------------


class ComponentHealth(BaseModel):
    status: str
    detail: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    app: str = "sourcelens"
    embedding_model: str
    embedding_loaded: bool
    vector_store: str
    llm_configured: bool
    llm_provider: Optional[str] = None
    documents_indexed: int
    chunks_indexed: int
    version: str = "0.1.0"


class PublicConfig(BaseModel):
    """Non-sensitive configuration exposed to the frontend."""

    llm_provider: Optional[str]
    llm_configured: bool
    embedding_model: str
    embedding_dim: int
    rag_top_k: int
    rag_min_relevance_score: float
    accepted_extensions: list[str]
    max_upload_mb: int
    max_files_per_upload: int
    max_query_length: int
    app_env: str


# --- Documents -------------------------------------------------------------


class DocumentInfo(BaseModel):
    document_id: str
    filename: str
    original_filename: str
    mime_type: str
    size_bytes: int
    chunk_count: int
    status: str
    created_at: str
    error: Optional[str] = None


class DocumentListResponse(BaseModel):
    documents: list[DocumentInfo]
    total_documents: int
    total_chunks: int


class UploadResult(DocumentInfo):
    pass


class UploadResponse(BaseModel):
    uploaded: int
    results: list[UploadResult]
    errors: list[dict] = Field(default_factory=list)


# --- Query -----------------------------------------------------------------


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    # Empty list means "search across all indexed documents".
    document_ids: list[str] = Field(default_factory=list)
    top_k: Optional[int] = None

    @field_validator("question")
    @classmethod
    def _strip(cls, v: str) -> str:
        return v.strip()


class Source(BaseModel):
    source_number: int
    filename: str
    page: Optional[int] = None
    chunk_id: str
    excerpt: str
    score: float


class QueryResponse(BaseModel):
    answer: str
    grounded: bool
    refusal_reason: Optional[str] = None
    sources: list[Source]
    retrieval: dict
    request_id: str


class ResetResponse(BaseModel):
    status: str
    documents_removed: int
    chunks_removed: int
