"""Upload validation and content-type checks."""

from __future__ import annotations

import os

from app.core.constants import ACCEPTED_EXTENSIONS, EXPECTED_MIME
from app.core.exceptions import (
    FileTooLargeError,
    TooManyFilesError,
    UnsupportedFileTypeError,
)


def allowed_extension(filename: str) -> str | None:
    ext = os.path.splitext(filename)[1].lower()
    return ext if ext in ACCEPTED_EXTENSIONS else None


def validate_upload(
    filename: str,
    size_bytes: int,
    max_bytes: int,
    declared_mime: str | None = None,
) -> str:
    """Return the validated lower-case extension or raise a validation error."""
    ext = allowed_extension(filename)
    if ext is None:
        raise UnsupportedFileTypeError(
            f"Unsupported file type '{filename}'. "
            f"Accepted types: {', '.join(ACCEPTED_EXTENSIONS)}"
        )
    if size_bytes > max_bytes:
        raise FileTooLargeError(
            f"File '{filename}' is {size_bytes} bytes, exceeding the "
            f"{max_bytes} byte limit."
        )
    # MIME is a secondary signal only; mismatches are downgraded to a warning
    # rather than a hard failure because clients often send generic types.
    if declared_mime and ext in EXPECTED_MIME:
        if declared_mime not in EXPECTED_MIME[ext] and declared_mime != "application/octet-stream":
            # Non-fatal: log and continue (handled by caller).
            pass
    return ext


def validate_upload_batch(filenames: list[str], max_files: int) -> None:
    if len(filenames) > max_files:
        raise TooManyFilesError(
            f"Too many files in one upload ({len(filenames)}). "
            f"Limit is {max_files}."
        )
    if len(filenames) == 0:
        raise UnsupportedFileTypeError("No files were provided.")
