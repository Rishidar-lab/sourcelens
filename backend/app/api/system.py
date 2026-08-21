"""Health and public configuration endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Request

from app.api.deps import get_container
from app.core.constants import ACCEPTED_EXTENSIONS
from app.schemas import HealthResponse, PublicConfig

router = APIRouter(prefix="/api", tags=["system"])


@router.get("/health", response_model=HealthResponse)
async def health(request: Request) -> HealthResponse:
    container = get_container(request)
    settings = container.settings
    provider = container.embedding_provider
    llm = container.llm_provider
    try:
        chunks = container.store.count_chunks()
        docs = container.store.count_documents()
        vector_status = "ready"
    except Exception:  # noqa: BLE001
        chunks, docs = 0, 0
        vector_status = "unavailable"

    llm_configured = bool(llm and llm.is_configured)
    return HealthResponse(
        status="ok" if vector_status == "ready" else "degraded",
        embedding_model=provider.model_name,
        embedding_loaded=provider.is_loaded,
        vector_store=vector_status,
        llm_configured=llm_configured,
        llm_provider=settings.llm_provider if settings.llm_provider != "none" else None,
        documents_indexed=docs,
        chunks_indexed=chunks,
    )


@router.get("/config/public", response_model=PublicConfig)
async def public_config(request: Request) -> PublicConfig:
    container = get_container(request)
    s = container.settings
    llm = container.llm_provider
    return PublicConfig(
        llm_provider=s.llm_provider if s.llm_provider != "none" else None,
        llm_configured=bool(llm and llm.is_configured),
        embedding_model=s.embedding_model,
        embedding_dim=s.embedding_dim,
        rag_top_k=s.rag_top_k,
        rag_min_relevance_score=s.rag_min_relevance_score,
        accepted_extensions=list(ACCEPTED_EXTENSIONS),
        max_upload_mb=s.max_upload_mb,
        max_files_per_upload=s.max_files_per_upload,
        max_query_length=s.max_query_length,
        app_env=s.app_env,
    )
