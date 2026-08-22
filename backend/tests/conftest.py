"""Shared pytest fixtures.

Tests run fully offline: a deterministic hash embedding provider replaces the
real ``SentenceTransformer`` model, and a mock LLM replaces any provider. A
fresh temporary Chroma directory is used per test.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.container import build_hash_container
from app.main import create_app
from app.services.documents import DocumentService
from app.services.llm.provider import MockLLMProvider

SAMPLES = Path(__file__).resolve().parent.parent.parent / "samples"


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        _env_file=None,
        app_env="test",
        chroma_persist_dir=str(tmp_path / "chroma"),
        data_dir=str(tmp_path / "data"),
        embedding_dim=384,
        rag_min_relevance_score=0.12,
        rag_top_k=5,
        max_upload_mb=20,
        max_files_per_upload=10,
    )


@pytest.fixture
def container(settings: Settings):
    return build_hash_container(settings)


@pytest.fixture
def document_service(container):
    return DocumentService(
        container.embedding_provider,
        container.store,
        container.chunker,
        max_bytes=container.settings.max_upload_bytes,
        max_files=container.settings.max_files_per_upload,
    )


@pytest.fixture
def mock_llm() -> MockLLMProvider:
    return MockLLMProvider()


@pytest.fixture
def client(container, mock_llm):
    # Replace the (possibly None) provider with the mock so RAG can answer.
    container.llm_provider = mock_llm
    container.rag._llm = mock_llm
    app = create_app(container)
    with TestClient(app) as c:
        yield c


@pytest.fixture
def client_bare(container):
    # No LLM provider configured (simulates missing credentials).
    app = create_app(container)
    with TestClient(app) as c:
        yield c


def sample_bytes(name: str) -> bytes:
    return (SAMPLES / name).read_bytes()


@pytest.fixture
def ingest_documents(document_service):
    """Helper that ingests a set of sample files for retrieval tests."""

    def _ingest(*names: str):
        files = [(n, sample_bytes(n)) for n in names]
        results, errors = document_service.ingest_files(files)
        assert not errors, f"Ingestion errors: {errors}"
        return results

    return _ingest
