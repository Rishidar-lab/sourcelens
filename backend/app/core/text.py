"""Shared lightweight tokenisation used by the hash embedding provider and the
retrieval relevance heuristics. Not a linguistic tokenizer - just enough to
compare content words between a query and a candidate chunk.
"""

from __future__ import annotations

import re

TOKEN_RE = re.compile(r"[a-z0-9]+")

STOPWORDS: frozenset[str] = frozenset(
    {
        "the", "a", "an", "and", "or", "but", "if", "then", "else", "of", "to", "in",
        "on", "at", "by", "for", "with", "as", "is", "are", "was", "were", "be", "been",
        "being", "it", "this", "that", "these", "those", "we", "you", "they", "he", "she",
        "our", "your", "their", "i", "my", "me", "from", "into", "about", "than", "so",
        "not", "no", "yes", "do", "does", "did", "can", "will", "would", "should", "may",
        "might", "must", "shall", "there", "here", "what", "which", "who", "whom", "how",
        "when", "where", "why", "all", "any", "each", "more", "most", "other", "some",
        "such", "only", "own", "same", "between", "through", "during", "before", "after",
    }
)


_STEM_SUFFIXES = ("ations", "ation", "ing", "ions", "ion", "ies", "es", "ed", "s")


def _stem(token: str) -> str:
    """Very small suffix-stripping stemmer.

    Not linguistically rigorous - it exists so obvious morphological variants
    ("instruct" / "instruction" / "instructions", "reader" / "readers") hash
    to the same bucket in the deterministic offline embedding and count as
    overlapping in the lexical relevance check. Only strips when at least 4
    characters remain, to avoid mangling short words.
    """
    for suf in _STEM_SUFFIXES:
        if token.endswith(suf) and len(token) - len(suf) >= 4:
            return token[: -len(suf)]
    return token


def content_tokens(text: str) -> set[str]:
    """Lower-cased, stopword-filtered, lightly-stemmed token set.

    Used both by the deterministic hash embedding provider (to build its
    vector) and by the retrieval relevance heuristics (to check lexical
    overlap between a question and a candidate chunk), so the two stay
    consistent.
    """
    return {
        _stem(t) for t in TOKEN_RE.findall(text.lower()) if t not in STOPWORDS
    }
