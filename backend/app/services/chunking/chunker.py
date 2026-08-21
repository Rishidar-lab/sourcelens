"""Recursive text chunking with source metadata preservation.

The splitter prefers paragraph, then sentence, then word boundaries so that
chunk boundaries stay as human-meaningful as possible. Each produced chunk
carries the original document id, filename, page (where known) and its index.
"""

from __future__ import annotations

import re
from typing import List

from app.core.constants import UNKNOWN_PAGE
from app.core.logging import get_logger
from app.models.domain import Chunk, ExtractedPage, new_id

logger = get_logger("sourcelens.chunking")

# Ordered separators tried by the recursive splitter, from strongest to weakest.
_SEPARATORS = ["\n\n", "\n", ". ", " ", ""]


def normalize_whitespace(text: str) -> str:
    """Collapse runs of whitespace without destroying paragraph breaks."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


class RecursiveChunker:
    def __init__(self, chunk_size: int = 900, chunk_overlap: int = 150) -> None:
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be smaller than chunk_size")
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def _split_recursive(self, text: str, seps: List[str]) -> List[str]:
        if not text:
            return []
        if len(text) <= self.chunk_size:
            return [text] if text.strip() else []

        sep = seps[0] if seps else ""
        if sep == "":
            # Hard character split.
            return [
                text[i : i + self.chunk_size]
                for i in range(0, len(text), self.chunk_size)
            ]

        parts = text.split(sep)
        merged: List[str] = []
        current = ""
        for part in parts:
            candidate = current + (sep if current else "") + part
            if len(candidate) > self.chunk_size and current:
                merged.append(current)
                current = part
            else:
                current = candidate
        if current:
            merged.append(current)

        # If any merged piece is still too large, recurse with a weaker separator.
        result: List[str] = []
        for piece in merged:
            if len(piece) > self.chunk_size and len(seps) > 1:
                result.extend(self._split_recursive(piece, seps[1:]))
            else:
                result.append(piece)
        return [r for r in result if r.strip()]

    def _with_overlap(self, pieces: List[str]) -> List[str]:
        if self.chunk_overlap <= 0 or len(pieces) <= 1:
            return pieces
        out: List[str] = []
        for i, piece in enumerate(pieces):
            if i == 0:
                out.append(piece)
                continue
            prev = out[-1]
            tail = prev[-self.chunk_overlap :] if len(prev) > self.chunk_overlap else prev
            # Only add overlap if it does not already end with the tail.
            if not piece.startswith(tail.strip()):
                out.append(tail + piece if tail.strip() else piece)
            else:
                out.append(piece)
        return out

    def chunk_pages(self, pages: List[ExtractedPage]) -> List[Chunk]:
        chunks: List[Chunk] = []
        for page in pages:
            text = normalize_whitespace(page.text)
            if not text:
                continue
            pieces = self._split_recursive(text, list(_SEPARATORS))
            pieces = self._with_overlap(pieces)
            for idx, piece in enumerate(pieces):
                piece = piece.strip()
                if not piece:
                    continue
                chunks.append(
                    Chunk(
                        chunk_id=new_id("chk"),
                        document_id=page.document_id,
                        filename=page.filename,
                        page=page.page if page.page != UNKNOWN_PAGE else UNKNOWN_PAGE,
                        chunk_index=idx,
                        text=piece,
                    )
                )
        logger.info(
            "chunking.complete",
            extra={"sl_document_id": pages[0].document_id if pages else "none",
                   "sl_chunks": len(chunks)},
        )
        return chunks
