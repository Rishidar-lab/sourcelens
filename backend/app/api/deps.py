"""FastAPI dependency helpers that resolve services from application state."""

from __future__ import annotations

from fastapi import Request

from app.container import Container
from app.services.documents import DocumentService


def get_container(request: Request) -> Container:
    return request.app.state.container


def get_document_service(request: Request) -> DocumentService:
    return request.app.state.document_service


def get_rag_service(request: Request):
    return request.app.state.container.rag
