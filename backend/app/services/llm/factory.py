"""Factory that builds the configured LLM provider from settings."""

from __future__ import annotations

from typing import Optional

from app.core.exceptions import LLMNotConfiguredError
from app.services.llm.provider import (
    GeminiProvider,
    LLMProvider,
    OpenAICompatibleProvider,
)

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com"


def build_llm_provider(
    provider: str,
    *,
    gemini_api_key: str = "",
    gemini_model: str = "gemini-1.5-flash",
    openai_api_key: str = "",
    openai_base_url: str = "https://api.openai.com/v1",
    openai_model: str = "gpt-4o-mini",
    ollama_base_url: str = "http://localhost:11434",
    ollama_model: str = "llama3.1",
    timeout_s: float = 60.0,
) -> Optional[LLMProvider]:
    if provider in (None, "none", ""):
        return None
    if provider == "gemini":
        return GeminiProvider(
            model=gemini_model,
            api_key=gemini_api_key,
            base_url=GEMINI_BASE_URL,
            timeout_s=timeout_s,
        )
    if provider == "openai":
        return OpenAICompatibleProvider(
            name="openai",
            model=openai_model,
            base_url=openai_base_url,
            api_key=openai_api_key,
            timeout_s=timeout_s,
        )
    if provider == "ollama":
        return OpenAICompatibleProvider(
            name="ollama",
            model=ollama_model,
            base_url=ollama_base_url,
            api_key="ollama",
            path="/v1/chat/completions",
            requires_key=False,
            timeout_s=timeout_s,
        )
    raise LLMNotConfiguredError(f"Unknown LLM provider '{provider}'.")
