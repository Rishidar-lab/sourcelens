from app.core.exceptions import (
    CorruptDocumentError,
    EmptyDocumentError,
    UnsupportedFileTypeError,
)
from app.services.ingestion.parsers import parse_by_extension
from app.services.ingestion.service import ingest_file, sanitize_filename


def test_txt_ingestion():
    text = b"Employees may work remotely up to 2 days per week.\nSecond line."
    meta, pages = ingest_file("policy.txt", text, max_bytes=10_000_000)
    assert meta.filename.endswith(".txt")
    assert len(pages) == 1
    assert "remotely" in pages[0].text


def test_pdf_ingestion():
    data = ( __import__("pathlib").Path(__file__).resolve().parent.parent.parent / "samples" / "incident-response-policy.pdf").read_bytes()
    meta, pages = ingest_file("incident.pdf", data, max_bytes=10_000_000)
    assert any("1 hour" in p.text for p in pages)


def test_unsupported_extension():
    try:
        ingest_file("malware.exe", b"x", max_bytes=10_000_000)
        assert False, "expected UnsupportedFileTypeError"
    except UnsupportedFileTypeError:
        pass


def test_empty_document():
    try:
        ingest_file("empty.txt", b"   \n\t  ", max_bytes=10_000_000)
        assert False, "expected EmptyDocumentError"
    except EmptyDocumentError:
        pass


def test_corrupt_pdf():
    try:
        parse_by_extension(b"%not a pdf%%%", filename="x.pdf", document_id="d", ext=".pdf")
        assert False, "expected CorruptDocumentError"
    except CorruptDocumentError:
        pass


def test_sanitize_filename():
    assert sanitize_filename("../../secret.txt") == "secret.txt"
    assert "/" not in sanitize_filename("a/b/c.pdf")
