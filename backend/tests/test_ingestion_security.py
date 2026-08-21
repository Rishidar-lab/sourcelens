import pytest

from app.core.exceptions import FileTooLargeError, TooManyFilesError
from app.services.ingestion.parsers import parse_by_extension
from app.services.ingestion.service import ingest_file, sanitize_filename


def test_duplicate_within_batch_is_rejected(document_service):
    data = b"Employees may work remotely up to three days per week."
    results, errors = document_service.ingest_files(
        [("policy.txt", data), ("policy-copy.txt", data)]
    )
    assert len(results) == 1
    assert len(errors) == 1
    assert errors[0]["code"] == "duplicate_document"


def test_duplicate_across_calls_is_rejected(document_service):
    data = b"Employees may work remotely up to three days per week."
    results1, errors1 = document_service.ingest_files([("policy.txt", data)])
    assert not errors1
    results2, errors2 = document_service.ingest_files([("policy-again.txt", data)])
    assert not results2
    assert errors2[0]["code"] == "duplicate_document"


def test_file_too_large_is_rejected():
    data = b"x" * 1000
    with pytest.raises(FileTooLargeError):
        ingest_file("big.txt", data, max_bytes=500)


def test_too_many_files_is_rejected(document_service):
    files = [(f"f{i}.txt", b"some content") for i in range(document_service._max_files + 1)]
    with pytest.raises(TooManyFilesError):
        document_service.ingest_files(files)


def test_unicode_filename_is_sanitized_not_rejected():
    name = sanitize_filename("résumé notes 简体字 report.txt")
    assert "/" not in name and "\\" not in name
    assert name.endswith(".txt")


def test_path_traversal_filename_is_flattened():
    assert sanitize_filename("../../../etc/passwd") == "passwd"
    # Windows-style separators aren't path components on a POSIX backend, but
    # must still never survive into the stored filename as literal slashes -
    # they are flattened to underscores, so no traversal or nesting is
    # possible either way.
    backslash_result = sanitize_filename("..\\..\\windows\\system32\\evil.txt")
    assert "/" not in backslash_result and "\\" not in backslash_result
    assert not backslash_result.startswith("..")


def test_whitespace_only_filename_falls_back_to_default():
    name = sanitize_filename("   ...   ")
    assert name == "document"


def test_executable_renamed_as_pdf_is_rejected_as_corrupt():
    exe_bytes = b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff" + b"\x00" * 64
    with pytest.raises(Exception):
        parse_by_extension(exe_bytes, filename="totally-a.pdf", document_id="d", ext=".pdf")


def test_damaged_docx_is_rejected_as_corrupt():
    # A .docx is a zip archive; random bytes are not a valid zip/OOXML package.
    with pytest.raises(Exception):
        parse_by_extension(b"not a real docx file", filename="broken.docx", document_id="d", ext=".docx")
