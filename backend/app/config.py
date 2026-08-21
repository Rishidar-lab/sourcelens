"""Application configuration loaded from environment variables.

All secrets are read from the environment only. No secret is ever hard-coded,
and the public config endpoint intentionally exposes only non-sensitive values.
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Runtime ---
    app_env: Literal["development", "production", "test"] = "development"
    backend_host: str = "127.0.0.1"
    backend_port: int = 8000
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:5173"

    # --- Data / storage ---
    data_dir: str = "./data"
    chroma_persist_dir: str = "./data/chroma"
    upload_tmp_dir: str = "./data/tmp"

    # --- Upload limits ---
    max_upload_mb: int = 20
    max_files_per_upload: int = 10
    max_query_length: int = 2000

    # --- Chunking ---
    chunk_size: int = 900
    chunk_overlap: int = 150

    # --- Embeddings ---
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dim: int = 384
    embedding_batch_size: int = 32
    embedding_normalize: bool = True

    # --- Retrieval / RAG ---
    rag_top_k: int = 5
    rag_min_relevance_score: float = 0.20
    # Similar chunks closer than this cosine distance are de-duplicated.
    rag_dedup_similarity: float = 0.97
    # Expand to adjacent chunks when a mid-chunk boundary is hit.
    rag_expand_adjacent: bool = True

    # --- LLM ---
    llm_provider: Literal["gemini", "openai", "ollama", "none"] = "none"

    gemini_api_key: str = ""
    gemini_model: str = "gemini-1.5-flash"

    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1"

    llm_temperature: float = 0.0
    llm_max_tokens: int = 1024
    llm_request_timeout_s: int = 60

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_configured_llm(self) -> bool:
        return self.llm_provider != "none" and self.llm_provider is not None

    def llm_ready(self) -> bool:
        if self.llm_provider == "none":
            return False
        if self.llm_provider == "gemini":
            return bool(self.gemini_api_key)
        if self.llm_provider == "openai":
            return bool(self.openai_api_key)
        if self.llm_provider == "ollama":
            return bool(self.ollama_base_url)
        return False


@lru_cache
def get_settings() -> Settings:
    return Settings()


def reset_settings() -> None:
    """Clear the cached settings (used by tests to re-read env overrides)."""
    get_settings.cache_clear()


def load_settings_from_env_file(path: str | None = None) -> Settings:
    """Load settings, optionally pointing pydantic at a specific .env file."""
    if path:
        os.environ.setdefault("SOURCELENS_ENV_FILE", path)
    return Settings(_env_file=path or ".env")
