from __future__ import annotations

import hashlib
import os
from pathlib import Path

from repopilot.repository.filters import (
    detect_language,
    get_extension,
    is_ignored_directory,
    is_supported_text_file,
)
from repopilot.repository.models import RepositoryScanResult, ScannedFile

DEFAULT_MAX_FILE_SIZE_BYTES = 1_000_000


class RepositoryScanError(ValueError):
    """Raised when a repository cannot be scanned."""


def scan_repository(
    root_path: str | Path,
    *,
    max_file_size_bytes: int = DEFAULT_MAX_FILE_SIZE_BYTES,
) -> RepositoryScanResult:
    """Scan supported text files under a repository root."""
    root = Path(root_path).expanduser()
    if not root.exists():
        raise RepositoryScanError(f"Repository root does not exist: {root}")
    if not root.is_dir():
        raise RepositoryScanError(f"Repository root is not a directory: {root}")
    if max_file_size_bytes < 0:
        raise RepositoryScanError(
            "max_file_size_bytes must be greater than or equal to 0"
        )

    root = root.resolve()
    scanned_files: list[ScannedFile] = []
    skipped_count = 0

    for current_root, directory_names, file_names in os.walk(root):
        directory_names[:] = sorted(
            name for name in directory_names if not is_ignored_directory(name)
        )

        for file_name in sorted(file_names):
            file_path = Path(current_root) / file_name
            scanned_file = _scan_file(
                root=root,
                file_path=file_path,
                max_file_size_bytes=max_file_size_bytes,
            )
            if scanned_file is None:
                skipped_count += 1
                continue
            scanned_files.append(scanned_file)

    total_size_bytes = sum(file.size_bytes for file in scanned_files)
    return RepositoryScanResult(
        root_name=root.name,
        file_count=len(scanned_files),
        total_size_bytes=total_size_bytes,
        files=scanned_files,
        skipped_count=skipped_count,
    )


def _scan_file(
    *,
    root: Path,
    file_path: Path,
    max_file_size_bytes: int,
) -> ScannedFile | None:
    if not file_path.is_file() or not is_supported_text_file(file_path):
        return None

    try:
        size_bytes = file_path.stat().st_size
    except OSError:
        return None

    if size_bytes > max_file_size_bytes:
        return None

    try:
        content = file_path.read_bytes()
    except OSError:
        return None

    if _is_binary_content(content):
        return None

    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        return None

    return ScannedFile(
        path=_relative_path(root=root, file_path=file_path),
        language=detect_language(file_path),
        extension=get_extension(file_path),
        size_bytes=size_bytes,
        line_count=_count_lines(text),
        sha256=hashlib.sha256(content).hexdigest(),
    )


def _relative_path(*, root: Path, file_path: Path) -> str:
    return file_path.relative_to(root).as_posix()


def _count_lines(text: str) -> int:
    if text == "":
        return 0
    return text.count("\n") + (0 if text.endswith("\n") else 1)


def _is_binary_content(content: bytes) -> bool:
    return b"\x00" in content
