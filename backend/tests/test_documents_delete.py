def test_delete_removes_metadata_and_vectors(document_service, ingest_documents, container):
    results = ingest_documents("employee-handbook.md")
    doc_id = results[0].document_id
    assert container.store.count_documents() == 1
    assert container.store.count_chunks() > 0

    removed_docs, removed_chunks = document_service.delete_document(doc_id)
    assert removed_docs == 1
    assert removed_chunks > 0
    assert container.store.count_documents() == 0
    assert container.store.count_chunks() == 0
    import pytest

    with pytest.raises(Exception):
        document_service.get_document(doc_id)
