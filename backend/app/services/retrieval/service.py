"""Retrieval service: turns a query into a ranked, filtered evidence set."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from app.core.logging import get_logger
from app.models.domain import RetrievedEvidence
from app.repositories.chroma_store import ChromaStore
from app.services.embeddings.provider import EmbeddingProvider

logger = get_logger("sourcelens.retrieval")


@dataclass
class RetrievalResult:
    evidence: list[RetrievedEvidence]
    chunks_considered: int
    best_score: float
    filtered_out: int = 0
    expanded: int = 0

    @property
    def has_evidence(self) -> bool:
        return bool(self.evidence)


def _contains_ratio(a: str, b: str) -> float:
    """Return the fraction of the shorter string contained in the longer."""
    a, b = a.strip(), b.strip()
    if not a or not b:
        return 0.0
    short, long = (a, b) if len(a) <= len(b) else (b, a)
    return len(short) / max(1, len(long))


class RetrievalService:
    def __init__(
        self,
        provider: EmbeddingProvider,
        store: ChromaStore,
        *,
        min_relevance_score: float = 0.20,
        dedup_containment: float = 0.9,
        expand_adjacent: bool = True,
    ) -> None:
        self._provider = provider
        self._store = store
        self._min_relevance = min_relevance_score
        self._dedup = dedup_containment
        self._expand = expand_adjacent

    def retrieve(
        self,
        question: str,
        *,
        top_k: int,
        document_ids: Optional[list[str]] = None,
        min_relevance_score: Optional[float] = None,
    ) -> RetrievalResult:
        min_rel = min_relevance_score if min_relevance_score is not None else self._min_relevance
        try:
            (query_vec,) = self._provider.embed([question])
        except Exception as exc:  # noqa: BLE001
            from app.core.exceptions import RetrievalError

            raise RetrievalError(f"Failed to embed query: {exc}") from exc

        raw = self._store.query(query_vec, top_k=top_k, document_ids=document_ids)
        chunks_considered = len(raw)

        # 1. Relevance filter.
        relevant = [e for e in raw if e.score >= min_rel]
        filtered_out = chunks_considered - len(relevant)

        # 2. De-duplicate near-identical chunks (overlap produces these).
        deduped: list[RetrievedEvidence] = []
        for ev in relevant:
            if any(
                _contains_ratio(ev.text, kept.text) >= self._dedup for kept in deduped
            ):
                continue
            deduped.append(ev)

        best = max((e.score for e in deduped), default=0.0)

        # 3. Optionally expand to adjacent chunks of the strongest evidence.
        expanded = 0
        if self._expand and deduped:
            neighbor_ids = set()
            for ev in list(deduped):
                neighbors = self._store.get_chunks_for_document(ev.document_id)
                for nb in neighbors:
                    if nb.chunk_id == ev.chunk_id:
                        continue
                    if abs(nb.chunk_index - ev.chunk_index) != 1:
                        continue
                    if nb.chunk_id in neighbor_ids:
                        continue
                    nb.score = round(ev.score * 0.92, 4)
                    deduped.append(nb)
                    neighbor_ids.add(nb.chunk_id)
                    expanded += 1

        deduped.sort(key=lambda e: e.score, reverse=True)
        logger.info(
            "retrieval.complete",
            extra={
                "sl_considered": chunks_considered,
                "sl_kept": len(deduped),
                "sl_best": round(best, 3),
            },
        )
        return RetrievalResult(
            evidence=deduped,
            chunks_considered=chunks_considered,
            best_score=best,
            filtered_out=filtered_out,
            expanded=expanded,
        )
