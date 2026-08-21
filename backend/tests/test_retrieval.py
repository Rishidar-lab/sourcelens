def test_relevant_chunk_retrieved(document_service, ingest_documents, container):
    ingest_documents("remote-work-policy.md", "employee-handbook.md")
    result = container.retrieval.retrieve(
        "remote work days per week permitted", top_k=5
    )
    assert result.has_evidence
    assert result.best_score >= container.settings.rag_min_relevance_score
    assert result.evidence[0].filename == "remote-work-policy.md"


def test_unrelated_query_not_grounded(document_service, ingest_documents, container):
    ingest_documents("remote-work-policy.md", "employee-handbook.md")
    result = container.retrieval.retrieve("FIFA world cup winner 2018", top_k=5)
    assert not result.has_evidence
    assert result.best_score < container.settings.rag_min_relevance_score
