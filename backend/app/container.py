"""Service container: wires the pipeline together from settings.

Tests build their own container with fake embedding / mock LLM providers so the
full pipeline can run without a model download or network access.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.config import Settings
from app.repositories.chroma_store import ChromaStore
from app.services.chunking.chunker import RecursiveChunker
from app.services.embeddings.provider import (
    DeterministicHashEmbeddingProvider,
    EmbeddingProvider,
    build_embedding_provider,
)
from app.services.llm.factory import build_llm_provider
from app.services.llm.provider import LLMProvider
from app.services.rag.service import RAGService
from app.services.retrieval.service import RetrievalService


@dataclass
class Container:
    settings: Settings
    embedding_provider: EmbeddingProvider
    store: ChromaStore
    retrieval: RetrievalService
    rag: RAGService
    llm_provider: Optional[LLMProvider]
    chunker: RecursiveChunker


def build_container(
    settings: Settings,
    *,
    embedding_provider: Optional[EmbeddingProvider] = None,
    llm_provider: Optional[LLMProvider] = None,
    store: Optional[ChromaStore] = None,
) -> Container:
    embedding_provider = embedding_provider or build_embedding_provider(
        settings.embedding_model,
        dim=settings.embedding_dim,
        normalize=settings.embedding_normalize,
        batch_size=settings.embedding_batch_size,
    )
    store = store or ChromaStore(settings.chroma_persist_dir)
    chunker = RecursiveChunker(settings.chunk_size, settings.chunk_overlap)
    retrieval = RetrievalService(
        embedding_provider,
        store,
        min_relevance_score=settings.rag_min_relevance_score,
        dedup_containment=settings.rag_dedup_similarity,
        expand_adjacent=settings.rag_expand_adjacent,
    )
    if llm_provider is None:
        llm_provider = build_llm_provider(
            settings.llm_provider,
            gemini_api_key=settings.gemini_api_key,
            gemini_model=settings.gemini_model,
            openai_api_key=settings.openai_api_key,
            openai_base_url=settings.openai_base_url,
            openai_model=settings.openai_model,
            ollama_base_url=settings.ollama_base_url,
            ollama_model=settings.ollama_model,
        )
    rag = RAGService(
        retrieval,
        store,
        llm_provider,
        min_relevance_score=settings.rag_min_relevance_score,
        llm_temperature=settings.llm_temperature,
        llm_max_tokens=settings.llm_max_tokens,
        llm_request_timeout_s=settings.llm_request_timeout_s,
    )
    return Container(
        settings=settings,
        embedding_provider=embedding_provider,
        store=store,
        retrieval=retrieval,
        rag=rag,
        llm_provider=llm_provider,
        chunker=chunker,
    )


def build_hash_container(settings: Settings) -> Container:
    """Offline container: deterministic embeddings, no real model."""
    return build_container(
        settings,
        embedding_provider=DeterministicHashEmbeddingProvider(
            dim=settings.embedding_dim, normalize=settings.embedding_normalize
        ),
    )
