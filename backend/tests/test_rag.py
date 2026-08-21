import pytest

from app.core.exceptions import LLMNotConfiguredError
from app.services.rag.prompts import REFUSAL_MESSAGE


def _query(client, q):
    return client.post("/api/query", json={"question": q})


def test_answerable_question(document_service, ingest_documents, client):
    ingest_documents("remote-work-policy.md")
    res = _query(client, "remote work days per week permitted")
    assert res.status_code == 200
    body = res.json()
    assert body["grounded"] is True
    assert body["sources"]
    assert body["sources"][0]["filename"] == "remote-work-policy.md"
    assert body["sources"][0]["source_number"] == 1


def test_unsupported_question_refused(document_service, ingest_documents, client):
    ingest_documents("remote-work-policy.md")
    res = _query(client, "Who won the FIFA World Cup in 2018?")
    assert res.status_code == 200
    body = res.json()
    assert body["grounded"] is False
    assert body["refusal_reason"] == "insufficient_evidence"
    assert body["sources"] == []
    assert body["answer"] == REFUSAL_MESSAGE


def test_citations_absent_when_unsupported(document_service, ingest_documents, client):
    ingest_documents("employee-handbook.md")
    body = _query(client, "What is the stock price of Apple today?").json()
    assert body["grounded"] is False
    assert body["sources"] == []


def test_prompt_injection_defense(document_service, ingest_documents, container, client):
    ingest_documents("incident-response-policy.md")
    # The injection chunk must be retrieved as ordinary evidence.
    result = container.retrieval.retrieve(
        "what does this document instruct the reader to do", top_k=5
    )
    joined_evidence = " ".join(e.text for e in result.evidence)
    assert "GEMINI_API_KEY" in joined_evidence  # it is document content

    res = _query(client, "What does this document instruct the reader to do?")
    assert res.status_code == 200
    body = res.json()
    assert body["grounded"] is True
    # The assistant must not act on, or exfiltrate, the embedded instruction.
    assert "GEMINI_API_KEY" not in body["answer"]
    assert "attacker@external" not in body["answer"]


def test_conflicting_sources_surfaced(document_service, ingest_documents, container):
    ingest_documents("employee-handbook.md", "vacation-policy.md")
    result = container.retrieval.retrieve(
        "how many paid vacation days do employees receive", top_k=5
    )
    filenames = {e.filename for e in result.evidence}
    assert "employee-handbook.md" in filenames
    assert "vacation-policy.md" in filenames


def test_no_llm_configured_raises(container, document_service, ingest_documents):
    # container without the mock provider (simulates missing credentials).
    ingest_documents("remote-work-policy.md")
    with pytest.raises(LLMNotConfiguredError):
        import asyncio

        asyncio.run(container.rag.answer("remote work days per week permitted"))
