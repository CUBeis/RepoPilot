from __future__ import annotations

from pathlib import Path

from repopilot.chunking.chunker import (
    DEFAULT_MAX_LINES_PER_CHUNK,
    DEFAULT_OVERLAP_LINES,
    CodeChunkingError,
    chunk_file,
)
from repopilot.chunking.models import CodeChunk
from repopilot.context.models import RepositoryContext
from repopilot.repository import scan_repository
from repopilot.repository.models import ScannedFile
from repopilot.retrieval.keyword import DEFAULT_TOP_K, retrieve_keyword_chunks


class ContextBuildError(RuntimeError):
    """Raised when scanned repository context cannot be built."""


def build_repository_context(
    root_path: str | Path,
    query: str,
    *,
    max_lines_per_chunk: int = DEFAULT_MAX_LINES_PER_CHUNK,
    overlap_lines: int = DEFAULT_OVERLAP_LINES,
    top_k: int = DEFAULT_TOP_K,
) -> RepositoryContext:
    """Scan, chunk, and retrieve repository context for a query."""
    scan_result = scan_repository(root_path)
    chunks = _chunk_scanned_files(
        root_path=root_path,
        scanned_files=scan_result.files,
        max_lines_per_chunk=max_lines_per_chunk,
        overlap_lines=overlap_lines,
    )
    retrieved_chunks = retrieve_keyword_chunks(chunks, query, top_k=top_k)

    return RepositoryContext(
        root_name=scan_result.root_name,
        scanned_file_count=scan_result.file_count,
        total_size_bytes=scan_result.total_size_bytes,
        skipped_file_count=scan_result.skipped_count,
        total_chunks=len(chunks),
        retrieved_chunks=retrieved_chunks,
    )


def _chunk_scanned_files(
    *,
    root_path: str | Path,
    scanned_files: list[ScannedFile],
    max_lines_per_chunk: int,
    overlap_lines: int,
) -> list[CodeChunk]:
    chunks: list[CodeChunk] = []
    for scanned_file in scanned_files:
        try:
            chunks.extend(
                chunk_file(
                    root_path,
                    scanned_file,
                    max_lines_per_chunk=max_lines_per_chunk,
                    overlap_lines=overlap_lines,
                )
            )
        except CodeChunkingError as error:
            raise ContextBuildError(
                f"Could not chunk scanned file '{scanned_file.path}': {error}"
            ) from error
    return chunks
