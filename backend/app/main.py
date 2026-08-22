"""FastAPI application factory and global wiring."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import documents, query, system
from app.config import get_settings
from app.container import Container, build_container
from app.core.exceptions import SourceLensError
from app.core.logging import configure_logging, get_logger
from app.services.documents import DocumentService

logger = get_logger("sourcelens.server")


def _init_state(app: FastAPI, container: Container) -> None:
    settings = container.settings
    os.makedirs(settings.data_dir, exist_ok=True)
    os.makedirs(settings.chroma_persist_dir, exist_ok=True)
    os.makedirs(settings.upload_tmp_dir, exist_ok=True)
    app.state.container = container
    app.state.document_service = DocumentService(
        container.embedding_provider,
        container.store,
        container.chunker,
        max_bytes=settings.max_upload_bytes,
        max_files=settings.max_files_per_upload,
    )


def create_app(container: Container | None = None) -> FastAPI:
    app = FastAPI(
        title="SourceLens",
        version="0.1.0",
        description="Evidence-grounded answers from your documents (RAG).",
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        settings = get_settings()
        configure_logging(settings.log_level)
        built = build_container(settings)
        _init_state(app, built)
        logger.info(
            "server.startup",
            extra={"sl_provider": settings.llm_provider, "sl_model": settings.embedding_model},
        )
        yield

    @asynccontextmanager
    async def _noop_lifespan(app: FastAPI):
        yield

    if container is not None:
        configure_logging(container.settings.log_level)
        _init_state(app, container)
        app.router.lifespan_context = _noop_lifespan
    else:
        app.router.lifespan_context = lifespan

    # CORS — explicit allow-list only.
    settings = container.settings if container else get_settings()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=False,
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    app.include_router(system.router)
    app.include_router(documents.router)
    app.include_router(query.router)

    @app.exception_handler(SourceLensError)
    async def _sl_error(request: Request, exc: SourceLensError):
        return JSONResponse(status_code=exc.status_code, content=exc.to_dict())

    @app.exception_handler(Exception)
    async def _generic_error(request: Request, exc: Exception):
        logger.error("server.unhandled", extra={"sl_error": repr(exc)}, exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "internal_error", "message": "An internal error occurred."}},
        )

    @app.get("/")
    async def root():
        return {"app": "sourcelens", "docs": "/docs"}

    return app


app = create_app()
