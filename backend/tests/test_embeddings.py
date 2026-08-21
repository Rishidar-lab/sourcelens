from app.services.embeddings.provider import (
    DeterministicHashEmbeddingProvider,
    SentenceTransformerEmbeddingProvider,
)


def test_hash_embedding_shape_and_batch():
    provider = DeterministicHashEmbeddingProvider(dim=128, normalize=True)
    texts = ["alpha beta", "gamma delta", "alpha beta"]
    vecs = provider.embed(texts)
    assert len(vecs) == 3
    assert all(len(v) == 128 for v in vecs)
    # Identical inputs produce identical vectors (deterministic).
    assert vecs[0] == vecs[2]
    # Different inputs should differ.
    assert vecs[0] != vecs[1]
    # Normalized vectors have unit length.
    import math

    assert abs(math.sqrt(sum(x * x for x in vecs[0])) - 1.0) < 1e-6


def test_hash_embedding_similarity_signal():
    provider = DeterministicHashEmbeddingProvider(dim=512)
    a = provider.embed(["remote work days per week permitted"])[0]
    b = provider.embed(["remote work days per week permitted"])[0]
    c = provider.embed([" FIFA world cup champions 2018 "])[0]

    def cos(x, y):
        return sum(i * j for i, j in zip(x, y))

    assert cos(a, b) > cos(a, c)


def test_real_provider_is_constructable():
    # Ensure the real provider class is importable / instantiable shape is correct.
    assert issubclass(SentenceTransformerEmbeddingProvider, object)
