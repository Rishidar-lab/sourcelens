"""Persistent ChromaDB repository for document metadata and chunk vectors."""

from __future__ import annotations

import os

import chromadb
from chromadb.config import Settings as ChromaSettings
from chromadb.telemetry.product import ProductTelemetryClient, ProductTelemetryEvent
from overrides import override

from app.core.constants import CHUNKS_COLLECTION, DOCUMENTS_COLLECTION, UNKNOWN_PAGE
from app.core.exceptions import VectorStoreError
from app.core.logging import get_logger
from app.models.domain import DocumentMeta, RetrievedEvidence

logger = get_logger("sourcelens.vectorstore")


class NoOpTelemetryClient(ProductTelemetryClient):
    """Replaces Chroma's default Posthog telemetry client.

    Chroma 0.5.23 ships pinned to ``posthog>=2.4.0`` with no upper bound. Newer
    posthog releases (this project pins 7.x) changed the free-function
    ``posthog.capture(distinct_id, event, properties)`` signature to no longer
    accept those positional arguments, so Chroma's internal capture call raises
    ``TypeError: capture() takes 1 positional argument but 3 were given`` on
    every operation. Chroma catches that exception internally so it never
    crashes the app, but it floods the logs on every single vector-store call.
    Setting ``anonymized_telemetry=False`` does NOT prevent this: Chroma still
    calls ``posthog.capture(...)`` and only relies on posthog's own internals
    to no-op, which happens *after* the broken call is made.

    This is a local single-user portfolio app with no need for product
    telemetry, so we swap in a client that never talks to posthog at all,
    via Chroma's own supported ``chroma_product_telemetry_impl`` setting.
    """

    @override
    def capture(self, event: ProductTelemetryEvent) -> None:
        return None


def _to_similarity(distance: float) -> float:
    """Chroma's cosine distance is 1 - cosine_similarity. Clamp to [0, 1]."""
    return max(0.0, min(1.0, 1.0 - float(distance)))


class ChromaStore:
    def __init__(self, persist_dir: str, distance: str = "cosine") -> None:
        self.persist_dir = persist_dir
        os.makedirs(persist_dir, exist_ok=True)
        try:
            self._client = chromadb.PersistentClient(
                path=persist_dir,
                settings=ChromaSettings(
                    anonymized_telemetry=False,
                    chroma_product_telemetry_impl=(
                        "app.repositories.chroma_store.NoOpTelemetryClient"
                    ),
                ),
            )
            self._chunks = self._client.get_or_create_collection(
                name=CHUNKS_COLLECTION,
                metadata={"hnsw:space": distance},
            )
            self._docs = self._client.get_or_create_collection(
                name=DOCUMENTS_COLLECTION,
            )
        except Exception as exc:  # noqa: BLE001
            raise VectorStoreError(f"Failed to initialise vector store: {exc}") from exc

    # --- Documents --------------------------------------------------------

    def add_document_meta(self, meta: DocumentMeta) -> None:
        try:
            self._docs.add(
                ids=[meta.document_id],
                documents=[meta.filename],
                metadatas=[
                    {
                        "document_id": meta.document_id,
                        "filename": meta.filename,
                        "original_filename": meta.original_filename,
                        "mime_type": meta.mime_type,
                        "size_bytes": meta.size_bytes,
                        "content_hash": meta.content_hash,
                        "chunk_count": meta.chunk_count,
                        "status": meta.status,
                        "created_at": meta.created_at,
                        "error": meta.error or "",
                    }
                ],
            )
        except Exception as exc:  # noqa: BLE001
            raise VectorStoreError(f"Failed to store document metadata: {exc}") from exc

    def document_exists_by_hash(self, content_hash: str) -> bool:
        try:
            res = self._docs.get(
                where={"content_hash": content_hash}, include=[]
            )
            return bool(res and res.get("ids"))
        except Exception:  # noqa: BLE001
            return False

    def get_document(self, document_id: str) -> DocumentMeta | None:
        try:
            res = self._docs.get(ids=[document_id], include=["metadatas"])
        except Exception as exc:  # noqa: BLE001
            raise VectorStoreError(f"Failed to read document: {exc}") from exc
        if not res or not res.get("ids"):
            return None
        return self._meta_from_record(res["ids"][0], res["metadatas"][0])

    def list_documents(self) -> list[DocumentMeta]:
        try:
            res = self._docs.get(include=["metadatas"])
        except Exception as exc:  # noqa: BLE001
            raise VectorStoreError(f"Failed to list documents: {exc}") from exc
        if not res or not res.get("ids"):
            return []
        return [
            self._meta_from_record(doc_id, meta)
            for doc_id, meta in zip(res["ids"], res["metadatas"], strict=True)
        ]

    @staticmethod
    def _meta_from_record(doc_id: str, meta: dict) -> DocumentMeta:
        return DocumentMeta(
            document_id=doc_id,
            filename=meta.get("filename", doc_id),
            original_filename=meta.get("original_filename", ""),
            mime_type=meta.get("mime_type", ""),
            size_bytes=int(meta.get("size_bytes", 0)),
            content_hash=meta.get("content_hash", ""),
            chunk_count=int(meta.get("chunk_count", 0)),
            status=meta.get("status", "indexed"),
            created_at=meta.get("created_at", ""),
            error=meta.get("error") or None,
        )

    # --- Chunks -----------------------------------------------------------

    def add_chunks(self, chunks: list, embeddings: list[list[float]]) -> None:
        if not chunks:
            return
        try:
            self._chunks.add(
                ids=[c.chunk_id for c in chunks],
                embeddings=embeddings,
                documents=[c.text for c in chunks],
                metadatas=[
                    {
                        "chunk_id": c.chunk_id,
                        "document_id": c.document_id,
                        "filename": c.filename,
                        "page": c.page,
                        "chunk_index": c.chunk_index,
                    }
                    for c in chunks
                ],
            )
        except Exception as exc:  # noqa: BLE001
            raise VectorStoreError(f"Failed to store chunks: {exc}") from exc

    def query(
        self,
        embedding: list[float],
        *,
        top_k: int,
        document_ids: list[str] | None = None,
    ) -> list[RetrievedEvidence]:
        # Never ask Chroma for more results than can exist. An empty collection
        # returns a clean "no evidence" result; a small collection is clamped
        # to its actual size instead of relying on Chroma's own internal
        # clamp-and-warn behaviour.
        available = self.count_chunks()
        if available == 0:
            return []
        effective_k = min(top_k, available)

        where = None
        if document_ids:
            where = {"document_id": {"$in": document_ids}}
        try:
            res = self._chunks.query(
                query_embeddings=[embedding],
                n_results=effective_k,
                where=where,
                include=["metadatas", "documents", "distances"],
            )
        except Exception as exc:  # noqa: BLE001
            raise VectorStoreError(f"Vector search failed: {exc}") from exc

        if not res or not res.get("ids") or not res["ids"][0]:
            return []

        out: list[RetrievedEvidence] = []
        ids = res["ids"][0]
        dists = res["distances"][0]
        metas = res["metadatas"][0]
        docs = res["documents"][0]
        for cid, dist, meta, text in zip(ids, dists, metas, docs, strict=True):
            out.append(
                RetrievedEvidence(
                    chunk_id=meta.get("chunk_id", cid),
                    document_id=meta.get("document_id", ""),
                    filename=meta.get("filename", ""),
                    page=int(meta.get("page", UNKNOWN_PAGE)),
                    chunk_index=int(meta.get("chunk_index", 0)),
                    score=_to_similarity(dist),
                    text=text or "",
                )
            )
        return out

    def get_chunks_for_document(self, document_id: str) -> list[RetrievedEvidence]:
        """Return all chunks for a document, ordered by chunk_index."""
        try:
            res = self._chunks.get(
                where={"document_id": document_id},
                include=["metadatas", "documents"],
            )
        except Exception as exc:  # noqa: BLE001
            raise VectorStoreError(f"Failed to read chunks: {exc}") from exc
        if not res or not res.get("ids"):
            return []
        items = []
        for cid, meta, text in zip(
            res["ids"], res["metadatas"], res["documents"], strict=True
        ):
            items.append(
                RetrievedEvidence(
                    chunk_id=meta.get("chunk_id", cid),
                    document_id=meta.get("document_id", document_id),
                    filename=meta.get("filename", ""),
                    page=int(meta.get("page", UNKNOWN_PAGE)),
                    chunk_index=int(meta.get("chunk_index", 0)),
                    score=0.0,
                    text=text or "",
                )
            )
        items.sort(key=lambda c: c.chunk_index)
        return items

    def delete_document(self, document_id: str) -> tuple[int, int]:
        docs_removed, chunks_removed = 0, 0
        try:
            dres = self._docs.get(ids=[document_id], include=[])
            if dres and dres.get("ids"):
                self._docs.delete(ids=[document_id])
                docs_removed = 1
            cres = self._chunks.get(
                where={"document_id": document_id}, include=[]
            )
            if cres and cres.get("ids"):
                self._chunks.delete(ids=cres["ids"])
                chunks_removed = len(cres["ids"])
        except Exception as exc:  # noqa: BLE001
            raise VectorStoreError(f"Failed to delete document: {exc}") from exc
        return docs_removed, chunks_removed

    def count_chunks(self) -> int:
        try:
            return int(self._chunks.count())
        except Exception:  # noqa: BLE001
            return 0

    def count_documents(self) -> int:
        try:
            return int(self._docs.count())
        except Exception:  # noqa: BLE001
            return 0

    def reset(self) -> None:
        try:
            self._client.delete_collection(CHUNKS_COLLECTION)
            self._client.delete_collection(DOCUMENTS_COLLECTION)
            self._chunks = self._client.get_or_create_collection(
                name=CHUNKS_COLLECTION, metadata={"hnsw:space": "cosine"}
            )
            self._docs = self._client.get_or_create_collection(
                name=DOCUMENTS_COLLECTION
            )
        except Exception as exc:  # noqa: BLE001
            raise VectorStoreError(f"Failed to reset store: {exc}") from exc
