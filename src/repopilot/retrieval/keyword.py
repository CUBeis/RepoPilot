from __future__ import annotations

import re
from collections.abc import Sequence

from repopilot.chunking.models import CodeChunk
from repopilot.retrieval.models import RetrievedChunk

DEFAULT_TOP_K = 5
DEFAULT_PATH_WEIGHT = 2.0
DEFAULT_TEXT_WEIGHT = 1.0
TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


class KeywordRetrievalError(ValueError):
    """Raised when keyword retrieval configuration is invalid."""


def retrieve_keyword_chunks(
    chunks: Sequence[CodeChunk],
    query: str,
    *,
    top_k: int = DEFAULT_TOP_K,
    path_weight: float = DEFAULT_PATH_WEIGHT,
    text_weight: float = DEFAULT_TEXT_WEIGHT,
) -> list[RetrievedChunk]:
    """Return top keyword-overlap matches for a natural language query."""
    _validate_config(
        top_k=top_k,
        path_weight=path_weight,
        text_weight=text_weight,
    )

    query_terms = set(_tokenize(query))
    if not chunks or not query_terms:
        return []

    results = [
        result
        for chunk in chunks
        if (
            result := _score_chunk(
                chunk=chunk,
                query_terms=query_terms,
                path_weight=path_weight,
                text_weight=text_weight,
            )
        )
        is not None
    ]

    results.sort(
        key=lambda result: (
            -result.score,
            result.chunk.path,
            result.chunk.chunk_index,
            result.chunk.start_line,
            result.chunk.end_line,
        )
    )
    return results[:top_k]


def _validate_config(
    *,
    top_k: int,
    path_weight: float,
    text_weight: float,
) -> None:
    if top_k <= 0:
        raise KeywordRetrievalError("top_k must be greater than 0")
    if path_weight < 0:
        raise KeywordRetrievalError("path_weight must be greater than or equal to 0")
    if text_weight < 0:
        raise KeywordRetrievalError("text_weight must be greater than or equal to 0")


def _score_chunk(
    *,
    chunk: CodeChunk,
    query_terms: set[str],
    path_weight: float,
    text_weight: float,
) -> RetrievedChunk | None:
    path_terms = set(_tokenize(chunk.path))
    text_terms = set(_tokenize(chunk.text))

    path_matches = query_terms & path_terms
    text_matches = query_terms & text_terms
    matched_terms = sorted(path_matches | text_matches)
    if not matched_terms:
        return None

    score = (len(path_matches) * path_weight) + (len(text_matches) * text_weight)
    return RetrievedChunk(
        chunk=chunk,
        score=score,
        matched_terms=matched_terms,
    )


def _tokenize(text: str) -> list[str]:
    return TOKEN_PATTERN.findall(text.lower())
