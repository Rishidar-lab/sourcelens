"""Query endpoint: RAG retrieval + grounded generation."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.api.deps import get_document_service, get_rag_service
from app.core.exceptions import NoDocumentsIndexedError
from app.schemas import QueryRequest, QueryResponse
from app.services.documents import DocumentService
from app.services.rag.service import RAGService

router = APIRouter(prefix="/api/query", tags=["query"])


@router.post("", response_model=QueryResponse)
async def query(
    body: QueryRequest,
    request: Request,
    rag: RAGService = Depends(get_rag_service),
    docs: DocumentService = Depends(get_document_service),
) -> QueryResponse:
    # Fast, clean failure when there is nothing to search.
    if docs._store.count_chunks() == 0:
        raise NoDocumentsIndexedError(
            "No documents are indexed yet. Upload documents before querying."
        )
    top_k = body.top_k or request.app.state.container.settings.rag_top_k
    return await rag.answer(
        body.question, document_ids=body.document_ids, top_k=top_k
    )
