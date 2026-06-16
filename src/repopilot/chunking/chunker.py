from __future__ import annotations

import hashlib
from pathlib import Path

from repopilot.chunking.models import CodeChunk
from repopilot.repository.models import ScannedFile

DEFAULT_MAX_LINES_PER_CHUNK = 80
DEFAULT_OVERLAP_LINES = 10


class CodeChunkingError(ValueError):
    """Raised when a file cannot be chunked safely."""


def chunk_file(
    root_path: str | Path,
    scanned_file: ScannedFile,
    *,
    max_lines_per_chunk: int = DEFAULT_MAX_LINES_PER_CHUNK,
    overlap_lines: int = DEFAULT_OVERLAP_LINES,
) -> list[CodeChunk]:
    """Split a scanned text file into deterministic line-based chunks."""
    _validate_chunking_config(
        max_lines_per_chunk=max_lines_per_chunk,
        overlap_lines=overlap_lines,
    )

    root = _resolve_root(root_path)
    file_path = _resolve_scanned_file(root=root, scanned_file=scanned_file)
    text = _read_text_file(file_path)
    lines = text.splitlines()
    if not lines:
        return []

    step_size = max_lines_per_chunk - overlap_lines
    relative_path = file_path.relative_to(root).as_posix()
    chunks: list[CodeChunk] = []
    chunk_index = 0
    start_index = 0

    while start_index < len(lines):
        end_index = min(start_index + max_lines_per_chunk, len(lines))
        chunk_text = "\n".join(lines[start_index:end_index])
        chunks.append(
            CodeChunk(
                path=relative_path,
                language=scanned_file.language,
                chunk_index=chunk_index,
                start_line=start_index + 1,
                end_line=end_index,
                text=chunk_text,
                sha256=_hash_text(chunk_text),
            )
        )

        if end_index == len(lines):
            break

        chunk_index += 1
        start_index += step_size

    return chunks


def _validate_chunking_config(
    *,
    max_lines_per_chunk: int,
    overlap_lines: int,
) -> None:
    if max_lines_per_chunk <= 0:
        raise CodeChunkingError("max_lines_per_chunk must be greater than 0")
    if overlap_lines < 0:
        raise CodeChunkingError("overlap_lines must be greater than or equal to 0")
    if overlap_lines >= max_lines_per_chunk:
        raise CodeChunkingError(
            "overlap_lines must be smaller than max_lines_per_chunk"
        )


def _resolve_root(root_path: str | Path) -> Path:
    root = Path(root_path).expanduser()
    if not root.exists():
        raise CodeChunkingError(f"Repository root does not exist: {root}")
    if not root.is_dir():
        raise CodeChunkingError(f"Repository root is not a directory: {root}")
    return root.resolve()


def _resolve_scanned_file(*, root: Path, scanned_file: ScannedFile) -> Path:
    scanned_path = Path(scanned_file.path)
    if scanned_path.is_absolute():
        raise CodeChunkingError("Scanned file path must be relative")

    file_path = (root / scanned_path).resolve()
    try:
        file_path.relative_to(root)
    except ValueError as error:
        raise CodeChunkingError(
            f"Scanned file path escapes repository root: {scanned_file.path}"
        ) from error

    if not file_path.is_file():
        raise CodeChunkingError(f"Scanned file does not exist: {scanned_file.path}")

    return file_path


def _read_text_file(file_path: Path) -> str:
    try:
        return file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError as error:
        raise CodeChunkingError(
            f"Scanned file is not valid UTF-8: {file_path}"
        ) from error
    except OSError as error:
        raise CodeChunkingError(f"Could not read scanned file: {file_path}") from error


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
