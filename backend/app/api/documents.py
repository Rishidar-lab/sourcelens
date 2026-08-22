"""Document upload / listing / deletion endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Request, UploadFile
from fastapi.responses import JSONResponse

from app.api.deps import get_document_service
from app.core.exceptions import (
    TooManyFilesError,
    UnsupportedFileTypeError,
)
from app.schemas import DocumentListResponse, ResetResponse, UploadResponse
from app.services.documents import DocumentService

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.post("/upload", response_model=UploadResponse)
async def upload_documents(
    request: Request,
    docs: DocumentService = Depends(get_document_service),
    files: list[UploadFile] = File(..., description="One or more documents"),
) -> UploadResponse:
    if not files:
        raise UnsupportedFileTypeError("No files were provided.")
    if len(files) > docs._max_files:
        raise TooManyFilesError(
            f"Too many files in one upload ({len(files)}). "
            f"Limit is {docs._max_files}."
        )
    loaded = []
    content_types: dict[str, str] = {}
    for f in files:
        data = await f.read()
        name = f.filename or "unnamed"
        loaded.append((name, data))
        if f.content_type:
            content_types[name] = f.content_type
    results, errors = docs.ingest_files(loaded, content_types=content_types)
    return UploadResponse(uploaded=len(results), results=results, errors=errors)


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    docs: DocumentService = Depends(get_document_service),
) -> DocumentListResponse:
    return docs.list_documents()


@router.get("/{document_id}")
async def get_document(
    document_id: str, docs: DocumentService = Depends(get_document_service)
):
    return docs.get_document(document_id)


@router.delete("/{document_id}")
async def delete_document(
    document_id: str, docs: DocumentService = Depends(get_document_service)
):
    removed_docs, removed_chunks = docs.delete_document(document_id)
    return {
        "status": "deleted",
        "document_id": document_id,
        "documents_removed": removed_docs,
        "chunks_removed": removed_chunks,
    }


@router.delete("")
async def reset_knowledge_base(
    request: Request, docs: DocumentService = Depends(get_document_service)
):
    settings = request.app.state.container.settings
    if settings.app_env == "production":
        return JSONResponse(
            status_code=403,
            content={"error": {"code": "forbidden", "message": "Reset is disabled in production."}},
        )
    removed_docs, removed_chunks = docs.reset()
    return ResetResponse(
        status="reset",
        documents_removed=removed_docs,
        chunks_removed=removed_chunks,
    )
