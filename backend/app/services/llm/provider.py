"""LLM provider abstraction.

SourceLens never trusts retrieved document text as instructions. The RAG layer
is responsible for composing a single prompt with clearly separated sections
(system policy, user question, and untrusted evidence delimited as data). Each
provider simply forwards that prompt to its backend.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional

import httpx

from app.core.exceptions import LLMNotConfiguredError, LLMProviderError
from app.core.logging import get_logger

logger = get_logger("sourcelens.llm")


@dataclass
class LLMMessage:
    role: str  # "system" | "user" | "assistant"
    content: str


@dataclass
class LLMResult:
    text: str
    model: str
    provider: str
    latency_ms: int
    usage: Optional[dict] = None


class LLMProvider(ABC):
    name: str = "base"
    model: str = ""

    @property
    def is_configured(self) -> bool:
        return True

    @abstractmethod
    async def complete(
        self,
        messages: List[LLMMessage],
        *,
        temperature: float = 0.0,
        max_tokens: int = 1024,
    ) -> LLMResult:
        ...


class MockLLMProvider(LLMProvider):
    """Deterministic provider for tests and offline demos.

    It never contacts a network and never exposes secrets. It produces an
    evidence-backed answer template so grounding/citation logic can be tested
    without a paid API key.
    """

    name = "mock"
    model = "mock-v1"

    def __init__(self, *, answer_template: Optional[str] = None) -> None:
        self._template = answer_template

    async def complete(self, messages, *, temperature=0.0, max_tokens=1024) -> LLMResult:
        user_msg = next((m for m in messages if m.role == "user"), None)
        system_msg = next((m for m in messages if m.role == "system"), None)
        user_text = user_msg.content if user_msg else ""
        # The mock is only ever called with grounded evidence present.
        # It must not reveal anything outside the supplied evidence.
        evidence_marker = "RETRIEVED EVIDENCE" in user_text
        if self._template:
            answer = self._template
        elif evidence_marker:
            answer = (
                "Based on the supplied documents, the evidence indicates the "
                "following. [1] I am stating only what the retrieved excerpts support."
            )
        else:
            answer = (
                "I could not find sufficient evidence in the uploaded documents "
                "to answer that question."
            )
        return LLMResult(
            text=answer,
            model=self.model,
            provider=self.name,
            latency_ms=1,
            usage={"mock": True},
        )


class OpenAICompatibleProvider(LLMProvider):
    def __init__(
        self,
        *,
        name: str,
        model: str,
        base_url: str,
        api_key: str,
        path: str = "/chat/completions",
    ) -> None:
        self.name = name
        self.model = model
        self._url = base_url.rstrip("/") + path
        self._api_key = api_key
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(60.0), headers={"Authorization": f"Bearer {api_key}"}
        )

    @property
    def is_configured(self) -> bool:
        return bool(self._api_key) and self._api_key not in ("", "ollama")

    async def complete(self, messages, *, temperature=0.0, max_tokens=1024) -> LLMResult:
        if not self.is_configured:
            raise LLMNotConfiguredError(f"LLM provider '{self.name}' is not configured.")
        payload = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        try:
            resp = await self._client.post(self._url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            text = data["choices"][0]["message"]["content"]
            return LLMResult(
                text=text,
                model=self.model,
                provider=self.name,
                latency_ms=int(resp.elapsed.total_seconds() * 1000),
                usage=data.get("usage"),
            )
        except httpx.HTTPStatusError as exc:
            raise LLMProviderError(
                f"{self.name} returned {exc.response.status_code}: "
                f"{exc.response.text[:300]}"
            ) from exc
        except httpx.HTTPError as exc:
            raise LLMProviderError(f"{self.name} request failed: {exc}") from exc
        except (KeyError, IndexError, json.JSONDecodeError) as exc:
            raise LLMProviderError(f"{self.name} returned an unexpected response.") from exc


class GeminiProvider(LLMProvider):
    def __init__(self, *, model: str, api_key: str, base_url: str) -> None:
        self.name = "gemini"
        self.model = model
        self._api_key = api_key
        self._url = (
            f"{base_url.rstrip('/')}/v1beta/models/{model}:generateContent"
        )
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(60.0))

    @property
    def is_configured(self) -> bool:
        return bool(self._api_key)

    async def complete(self, messages, *, temperature=0.0, max_tokens=1024) -> LLMResult:
        if not self.is_configured:
            raise LLMNotConfiguredError("Gemini is not configured (missing API key).")
        system_text = next((m.content for m in messages if m.role == "system"), "")
        user_text = next((m.content for m in messages if m.role == "user"), "")
        payload = {
            "system_instruction": {"parts": [{"text": system_text}]},
            "contents": [{"role": "user", "parts": [{"text": user_text}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }
        try:
            resp = await self._client.post(self._url, params={"key": self._api_key}, json=payload)
            resp.raise_for_status()
            data = resp.json()
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            return LLMResult(
                text=text,
                model=self.model,
                provider=self.name,
                latency_ms=int(resp.elapsed.total_seconds() * 1000),
                usage=None,
            )
        except httpx.HTTPStatusError as exc:
            raise LLMProviderError(
                f"gemini returned {exc.response.status_code}: {exc.response.text[:300]}"
            ) from exc
        except httpx.HTTPError as exc:
            raise LLMProviderError(f"gemini request failed: {exc}") from exc
        except (KeyError, IndexError, json.JSONDecodeError) as exc:
            raise LLMProviderError("gemini returned an unexpected response.") from exc
