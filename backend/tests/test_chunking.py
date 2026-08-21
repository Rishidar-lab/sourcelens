from app.models.domain import ExtractedPage
from app.services.chunking.chunker import RecursiveChunker


def _pages(text: str, page: int = 1):
    return [ExtractedPage(document_id="doc1", filename="f.md", page=page, text=text)]


def test_chunks_within_size_bounds():
    text = ("Sentence number {} about remote work policy. ").format
    long = "".join(text(i) for i in range(40))
    chunks = RecursiveChunker(chunk_size=80, chunk_overlap=20).chunk_pages(_pages(long))
    assert len(chunks) > 1
    for c in chunks:
        assert len(c.text) <= 80 + 1


def test_overlap_between_adjacent_chunks():
    long = " ".join(f"word{i}" for i in range(60))
    chunks = RecursiveChunker(chunk_size=60, chunk_overlap=15).chunk_pages(_pages(long))
    assert len(chunks) >= 2
    overlapped = any(
        chunks[i + 1].text.startswith(chunks[i].text[-15:])
        for i in range(len(chunks) - 1)
    )
    assert overlapped, "expected overlap region between adjacent chunks"


def test_metadata_preserved():
    pages = [
        ExtractedPage(document_id="docX", filename="handbook.pdf", page=7, text="Alpha beta gamma. " * 40)
    ]
    chunks = RecursiveChunker(chunk_size=40, chunk_overlap=10).chunk_pages(pages)
    assert chunks[0].document_id == "docX"
    assert chunks[0].filename == "handbook.pdf"
    assert chunks[0].page == 7
    assert chunks[0].chunk_index == 0
    assert all(c.chunk_index == i for i, c in enumerate(chunks))


def test_empty_text_yields_no_chunks():
    chunks = RecursiveChunker().chunk_pages(_pages("   "))
    assert chunks == []
