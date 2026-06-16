from __future__ import annotations

from pathlib import Path, PurePosixPath, PureWindowsPath

from repopilot.tools.models import FileReadResult

DEFAULT_MAX_BYTES = 200_000
DEFAULT_MAX_LINES = 500


class FileToolError(ValueError):
    """Raised when a read-only file tool request is unsafe or invalid."""


def read_text_file(
    root_path: str | Path,
    relative_path: str,
    *,
    max_bytes: int = DEFAULT_MAX_BYTES,
    max_lines: int = DEFAULT_MAX_LINES,
) -> FileReadResult:
    """Read a whole UTF-8 text file with safety limits."""
    _validate_positive_limit(max_bytes, name="max_bytes")
    _validate_positive_limit(max_lines, name="max_lines")

    root = _resolve_root(root_path)
    file_path = _resolve_relative_file(root=root, relative_path=relative_path)
    content = _read_utf8_content(file_path=file_path, max_bytes=max_bytes)
    total_lines = _count_lines(content)
    if total_lines > max_lines:
        raise FileToolError(
            f"File exceeds max_lines limit: {total_lines} > {max_lines}"
        )

    return FileReadResult(
        path=_relative_posix_path(root=root, file_path=file_path),
        start_line=1 if total_lines else 0,
        end_line=total_lines,
        content=content,
        total_lines=total_lines,
        size_bytes=file_path.stat().st_size,
    )


def read_text_file_lines(
    root_path: str | Path,
    relative_path: str,
    start_line: int,
    end_line: int,
    *,
    max_bytes: int = DEFAULT_MAX_BYTES,
) -> FileReadResult:
    """Read an inclusive 1-based line range from a UTF-8 text file."""
    _validate_positive_limit(max_bytes, name="max_bytes")
    _validate_line_range(start_line=start_line, end_line=end_line)

    root = _resolve_root(root_path)
    file_path = _resolve_relative_file(root=root, relative_path=relative_path)
    content = _read_utf8_content(file_path=file_path, max_bytes=max_bytes)
    lines = content.splitlines()
    total_lines = _count_lines(content)

    if start_line > total_lines:
        raise FileToolError(
            f"start_line exceeds total lines: {start_line} > {total_lines}"
        )
    if end_line > total_lines:
        raise FileToolError(f"end_line exceeds total lines: {end_line} > {total_lines}")

    selected_content = "\n".join(lines[start_line - 1 : end_line])
    return FileReadResult(
        path=_relative_posix_path(root=root, file_path=file_path),
        start_line=start_line,
        end_line=end_line,
        content=selected_content,
        total_lines=total_lines,
        size_bytes=file_path.stat().st_size,
    )


def _resolve_root(root_path: str | Path) -> Path:
    root = Path(root_path).expanduser()
    if not root.exists():
        raise FileToolError(f"Repository root does not exist: {root}")
    if not root.is_dir():
        raise FileToolError(f"Repository root is not a directory: {root}")
    return root.resolve()


def _resolve_relative_file(*, root: Path, relative_path: str) -> Path:
    if not relative_path.strip():
        raise FileToolError("relative_path must not be empty")
    if _is_absolute_path(relative_path):
        raise FileToolError("relative_path must not be absolute")

    file_path = (root / relative_path).resolve()
    try:
        file_path.relative_to(root)
    except ValueError as error:
        raise FileToolError(
            f"relative_path escapes repository root: {relative_path}"
        ) from error

    if not file_path.exists():
        raise FileToolError(f"File does not exist: {relative_path}")
    if file_path.is_dir():
        raise FileToolError(f"Path is a directory, not a file: {relative_path}")
    if not file_path.is_file():
        raise FileToolError(f"Path is not a regular file: {relative_path}")

    return file_path


def _is_absolute_path(path: str) -> bool:
    return (
        Path(path).is_absolute()
        or PureWindowsPath(path).is_absolute()
        or PurePosixPath(path).is_absolute()
        or path.startswith(("/", "\\"))
    )


def _read_utf8_content(*, file_path: Path, max_bytes: int) -> str:
    size_bytes = file_path.stat().st_size
    if size_bytes > max_bytes:
        raise FileToolError(f"File exceeds max_bytes limit: {size_bytes} > {max_bytes}")

    try:
        content_bytes = file_path.read_bytes()
    except OSError as error:
        raise FileToolError(f"Could not read file: {file_path}") from error

    if b"\x00" in content_bytes:
        raise FileToolError(f"File appears to be binary: {file_path}")

    try:
        return content_bytes.decode("utf-8")
    except UnicodeDecodeError as error:
        raise FileToolError(f"File is not valid UTF-8: {file_path}") from error


def _validate_positive_limit(value: int, *, name: str) -> None:
    if value <= 0:
        raise FileToolError(f"{name} must be greater than 0")


def _validate_line_range(*, start_line: int, end_line: int) -> None:
    if start_line < 1:
        raise FileToolError("start_line must be greater than or equal to 1")
    if end_line < start_line:
        raise FileToolError("end_line must be greater than or equal to start_line")


def _count_lines(text: str) -> int:
    if text == "":
        return 0
    return text.count("\n") + (0 if text.endswith("\n") else 1)


def _relative_posix_path(*, root: Path, file_path: Path) -> str:
    return file_path.relative_to(root).as_posix()
