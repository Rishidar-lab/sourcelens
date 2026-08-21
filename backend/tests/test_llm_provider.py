from app.services.llm.factory import build_llm_provider
from app.services.llm.provider import OpenAICompatibleProvider


def test_ollama_provider_is_configured_without_real_api_key():
    """Regression test: the ollama provider used to be built with the literal
    placeholder api_key="ollama", and OpenAICompatibleProvider.is_configured
    explicitly excluded that exact string - so a locally running Ollama could
    never be reported as configured. Ollama doesn't authenticate at all, so
    is_configured must not depend on the placeholder key."""
    provider = build_llm_provider(
        "ollama", ollama_base_url="http://localhost:11434", ollama_model="llama3.1"
    )
    assert isinstance(provider, OpenAICompatibleProvider)
    assert provider.is_configured is True


def test_openai_provider_requires_a_real_key():
    unset = build_llm_provider("openai", openai_api_key="")
    configured = build_llm_provider("openai", openai_api_key="sk-real-key")
    assert unset.is_configured is False
    assert configured.is_configured is True
