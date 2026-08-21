"""Domain exceptions mapped to HTTP responses.

Every error returned to the API is an instance of :class:`SourceLensError`, which
carries an HTTP status code and a safe, user-facing message. Internal details
(stacks, paths, secrets) are never placed in the message.
"""

from __future__ import annotations

from typing import Any


class SourceLensError(Exception):
    status_code: int = 500
    code: str = "internal_error"

    def __init__(self, message: str, *, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        return {"error": {"code": self.code, "message": self.message, **self.details}}


class ValidationError(SourceLensError):
    status_code = 422
    code = "validation_error"


class UnsupportedFileTypeError(ValidationError):
    code = "unsupported_file_type"


class FileTooLargeError(ValidationError):
    code = "file_too_large"


class TooManyFilesError(ValidationError):
    code = "too_many_files"


class EmptyDocumentError(SourceLensError):
    status_code = 422
    code = "empty_document"


class CorruptDocumentError(SourceLensError):
    status_code = 422
    code = "corrupt_document"


class DuplicateDocumentError(SourceLensError):
    status_code = 409
    code = "duplicate_document"


class IngestionError(SourceLensError):
    status_code = 500
    code = "ingestion_failed"


class EmbeddingError(SourceLensError):
    status_code = 500
    code = "embedding_failed"


class VectorStoreError(SourceLensError):
    status_code = 500
    code = "vector_store_error"


class RetrievalError(SourceLensError):
    status_code = 500
    code = "retrieval_failed"


class NoDocumentsIndexedError(SourceLensError):
    status_code = 409
    code = "no_documents_indexed"


class LLMNotConfiguredError(SourceLensError):
    status_code = 503
    code = "llm_not_configured"


class LLMProviderError(SourceLensError):
    status_code = 502
    code = "llm_provider_error"


class DocumentNotFoundError(SourceLensError):
    status_code = 404
    code = "document_not_found"


class DeletionError(SourceLensError):
    status_code = 500
    code = "deletion_failed"
