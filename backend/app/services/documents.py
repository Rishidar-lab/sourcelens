"""Document ingestion orchestration used by the API layer."""

from __future__ import annotations

from typing import List, Tuple

from app.core.exceptions import (
    DocumentNotFoundError,
    DuplicateDocumentError,
    IngestionError,
    VectorStoreError,
)
from app.core.logging import get_logger
from app.models.domain import DocumentMeta
from app.repositories.chroma_store import ChromaStore
from app.schemas import DocumentInfo, DocumentListResponse, UploadResult
from app.services.chunking.chunker import RecursiveChunker
from app.services.embeddings.provider import EmbeddingProvider
from app.services.ingestion.service import ingest_file
from app.services.ingestion.validation import validate_upload_batch

logger = get_logger("sourcelens.documents")


class DocumentService:
    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        store: ChromaStore,
        chunker: RecursiveChunker,
        *,
        max_bytes: int,
        max_files: int,
    ) -> None:
        self._embed = embedding_provider
        self._store = store
        self._chunker = chunker
        self._max_bytes = max_bytes
        self._max_files = max_files

    def ingest_files(
        self, files: List[Tuple[str, bytes]]
    ) -> Tuple[List[UploadResult], List[dict]]:
        validate_upload_batch([f[0] for f in files], self._max_files)
        results: List[UploadResult] = []
        errors: List[dict] = []
        seen_hashes = set()

        for filename, data in files:
            try:
                meta, pages = ingest_file(
                    filename, data, max_bytes=self._max_bytes, seen_hashes=seen_hashes
                )
                if self._store.document_exists_by_hash(meta.content_hash):
                    raise DuplicateDocumentError(
                        f"'{meta.filename}' has already been indexed."
                    )
                chunks = self._chunker.chunk_pages(pages)
                if not chunks:
                    raise IngestionError(
                        f"'{meta.filename}' produced no indexable content."
                    )
                embeddings = self._embed.embed([c.text for c in chunks])
                self._store.add_chunks(chunks, embeddings)
                meta.chunk_count = len(chunks)
                self._store.add_document_meta(meta)
                seen_hashes.add(meta.content_hash)
                results.append(UploadResult(**meta.model_dump()))
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "ingestion.failed",
                    extra={"sl_filename": filename, "sl_error": type(exc).__name__},
                )
                errors.append(
                    {
                        "filename": filename,
                        "code": getattr(exc, "code", "error"),
                        "message": getattr(exc, "message", str(exc)),
                    }
                )
        return results, errors

    def list_documents(self) -> DocumentListResponse:
        metas = self._store.list_documents()
        infos = [DocumentInfo(**m.model_dump()) for m in metas]
        total_chunks = sum(m.chunk_count for m in metas)
        return DocumentListResponse(
            documents=infos,
            total_documents=len(infos),
            total_chunks=total_chunks,
        )

    def get_document(self, document_id: str) -> DocumentInfo:
        meta = self._store.get_document(document_id)
        if meta is None:
            raise DocumentNotFoundError(f"Document '{document_id}' was not found.")
        return DocumentInfo(**meta.model_dump())

    def delete_document(self, document_id: str) -> Tuple[int, int]:
        if self._store.get_document(document_id) is None:
            raise DocumentNotFoundError(f"Document '{document_id}' was not found.")
        try:
            return self._store.delete_document(document_id)
        except VectorStoreError:
            raise
        except Exception as exc:  # noqa: BLE001
            from app.core.exceptions import DeletionError

            raise DeletionError(f"Failed to delete document: {exc}") from exc

    def reset(self) -> Tuple[int, int]:
        docs = self._store.count_documents()
        chunks = self._store.count_chunks()
        self._store.reset()
        return docs, chunks
