

def test_health_ok(client_bare):
    res = client_bare.get("/api/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert body["embedding_loaded"] is True
    assert body["vector_store"] == "ready"
    assert body["documents_indexed"] == 0


def test_public_config(client_bare):
    res = client_bare.get("/api/config/public")
    assert res.status_code == 200
    body = res.json()
    assert body["embedding_model"]
    assert body["accepted_extensions"]
    assert body["max_upload_mb"] > 0
    # Secrets must never appear.
    assert "api_key" not in body
    assert "GEMINI" not in str(body).upper() or "gemini_api_key" not in body
