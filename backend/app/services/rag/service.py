"""RAG orchestration: retrieval + grounding gate + LLM + citations."""

from __future__ import annotations

import time
import uuid
from typing import Optional

from app.core.exceptions import LLMNotConfiguredError
from app.core.logging import get_logger
from app.models.domain import RetrievedEvidence
from app.repositories.chroma_store import ChromaStore
from app.schemas import QueryResponse, Source
from app.services.llm.provider import LLMMessage, LLMProvider
from app.services.rag.prompts import (
    REFUSAL_MESSAGE,
    SYSTEM_PROMPT,
    build_user_prompt,
)
from app.services.retrieval.service import RetrievalResult, RetrievalService

logger = get_logger("sourcelens.rag")

# Below this best-score the evidence is treated as insufficient, regardless of
# what the LLM might volunteer.
INSUFFICIENT_FLOOR = 0.0


class RAGService:
    def __init__(
        self,
        retrieval: RetrievalService,
        store: ChromaStore,
        llm_provider: Optional[LLMProvider],
        *,
        min_relevance_score: float = 0.20,
        llm_temperature: float = 0.0,
        llm_max_tokens: int = 1024,
        llm_request_timeout_s: int = 60,
    ) -> None:
        self._retrieval = retrieval
        self._store = store
        self._llm = llm_provider
        self._min_relevance = min_relevance_score
        self._temperature = llm_temperature
        self._max_tokens = llm_max_tokens
        self._timeout = llm_request_timeout_s

    async def answer(
        self,
        question: str,
        *,
        document_ids: Optional[list[str]] = None,
        top_k: Optional[int] = None,
    ) -> QueryResponse:
        start = time.time()
        effective_top_k = top_k or 5

        retrieval: RetrievalResult = self._retrieval.retrieve(
            question,
            top_k=effective_top_k,
            document_ids=document_ids,
            min_relevance_score=self._min_relevance,
        )

        # --- Evidence sufficiency gate (defence in depth) ---
        if not retrieval.has_evidence or retrieval.best_score < self._min_relevance:
            latency = int((time.time() - start) * 1000)
            logger.info(
                "rag.refusal",
                extra={"sl_reason": "insufficient_evidence", "sl_best": round(retrieval.best_score, 3)},
            )
            return QueryResponse(
                answer=REFUSAL_MESSAGE,
                grounded=False,
                refusal_reason="insufficient_evidence",
                sources=[],
                retrieval={
                    "chunks_considered": retrieval.chunks_considered,
                    "best_score": round(retrieval.best_score, 4),
                    "filtered_out": retrieval.filtered_out,
                    "expanded": retrieval.expanded,
                    "top_k": effective_top_k,
                    "latency_ms": latency,
                },
                request_id=uuid.uuid4().hex,
            )

        if self._llm is None or not self._llm.is_configured:
            raise LLMNotConfiguredError(
                "No LLM is configured. Set LLM_PROVIDER and the relevant API "
                "credentials, or start an Ollama-compatible endpoint."
            )

        evidence = retrieval.evidence
        user_prompt = build_user_prompt(question, evidence)
        result = await self._llm.complete(
            [LLMMessage(role="system", content=SYSTEM_PROMPT),
             LLMMessage(role="user", content=user_prompt)],
            temperature=self._temperature,
            max_tokens=self._max_tokens,
        )

        sources = self._build_sources(evidence)
        latency = int((time.time() - start) * 1000)
        logger.info(
            "rag.complete",
            extra={"sl_sources": len(sources), "sl_latency_ms": latency},
        )
        return QueryResponse(
            answer=result.text.strip(),
            grounded=True,
            sources=sources,
            retrieval={
                "chunks_considered": retrieval.chunks_considered,
                "best_score": round(retrieval.best_score, 4),
                "filtered_out": retrieval.filtered_out,
                "expanded": retrieval.expanded,
                "top_k": effective_top_k,
                "latency_ms": latency,
                "provider": result.provider,
                "model": result.model,
            },
            request_id=uuid.uuid4().hex,
        )

    @staticmethod
    def _build_sources(evidence: list[RetrievedEvidence]) -> list[Source]:
        sources: list[Source] = []
        for i, ev in enumerate(evidence, start=1):
            excerpt = ev.text
            if len(excerpt) > 600:
                excerpt = excerpt[:597].rstrip() + "..."
            sources.append(
                Source(
                    source_number=i,
                    filename=ev.filename,
                    page=ev.page if ev.page and ev.page > 0 else None,
                    chunk_id=ev.chunk_id,
                    excerpt=excerpt,
                    score=round(ev.score, 4),
                )
            )
        return sources
