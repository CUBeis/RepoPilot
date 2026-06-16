import hashlib
from pathlib import Path

import pytest

from repopilot.chunking.chunker import CodeChunkingError, chunk_file
from repopilot.repository.models import ScannedFile


def make_scanned_file(path: str, *, language: str | None = "python") -> ScannedFile:
    return ScannedFile(
        path=path,
        language=language,
        extension=Path(path).suffix,
        size_bytes=0,
        line_count=0,
        sha256="",
    )


def write_lines(path: Path, line_count: int) -> str:
    text = "\n".join(f"line {line_number}" for line_number in range(1, line_count + 1))
    path.write_text(text, encoding="utf-8")
    return text


def test_chunks_small_file_into_one_chunk(tmp_path: Path) -> None:
    file_path = tmp_path / "app.py"
    write_lines(file_path, 3)

    chunks = chunk_file(tmp_path, make_scanned_file("app.py"))

    assert len(chunks) == 1
    assert chunks[0].path == "app.py"
    assert chunks[0].language == "python"
    assert chunks[0].chunk_index == 0
    assert chunks[0].start_line == 1
    assert chunks[0].end_line == 3
    assert chunks[0].text == "line 1\nline 2\nline 3"


def test_chunks_large_file_into_multiple_chunks(tmp_path: Path) -> None:
    file_path = tmp_path / "app.py"
    write_lines(file_path, 12)

    chunks = chunk_file(
        tmp_path,
        make_scanned_file("app.py"),
        max_lines_per_chunk=5,
        overlap_lines=2,
    )

    assert len(chunks) == 4
    assert [chunk.chunk_index for chunk in chunks] == [0, 1, 2, 3]


def test_includes_line_overlap_between_chunks(tmp_path: Path) -> None:
    file_path = tmp_path / "app.py"
    write_lines(file_path, 8)

    chunks = chunk_file(
        tmp_path,
        make_scanned_file("app.py"),
        max_lines_per_chunk=5,
        overlap_lines=2,
    )

    first_lines = chunks[0].text.splitlines()
    second_lines = chunks[1].text.splitlines()
    assert first_lines[-2:] == ["line 4", "line 5"]
    assert second_lines[:2] == ["line 4", "line 5"]


def test_returns_correct_start_and_end_lines(tmp_path: Path) -> None:
    file_path = tmp_path / "app.py"
    write_lines(file_path, 12)

    chunks = chunk_file(
        tmp_path,
        make_scanned_file("app.py"),
        max_lines_per_chunk=5,
        overlap_lines=2,
    )

    assert [(chunk.start_line, chunk.end_line) for chunk in chunks] == [
        (1, 5),
        (4, 8),
        (7, 11),
        (10, 12),
    ]


def test_calculates_sha256_for_chunk_text(tmp_path: Path) -> None:
    file_path = tmp_path / "app.py"
    write_lines(file_path, 3)

    chunks = chunk_file(tmp_path, make_scanned_file("app.py"))

    expected_hash = hashlib.sha256(chunks[0].text.encode("utf-8")).hexdigest()
    assert chunks[0].sha256 == expected_hash


def test_skips_empty_files(tmp_path: Path) -> None:
    (tmp_path / "empty.py").write_text("", encoding="utf-8")

    chunks = chunk_file(tmp_path, make_scanned_file("empty.py"))

    assert chunks == []


def test_raises_clear_error_when_overlap_is_too_large(tmp_path: Path) -> None:
    (tmp_path / "app.py").write_text("print('hello')", encoding="utf-8")

    with pytest.raises(CodeChunkingError, match="overlap_lines"):
        chunk_file(
            tmp_path,
            make_scanned_file("app.py"),
            max_lines_per_chunk=5,
            overlap_lines=5,
        )


def test_raises_clear_error_if_file_path_escapes_root(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (tmp_path / "outside.py").write_text("print('outside')", encoding="utf-8")

    with pytest.raises(CodeChunkingError, match="escapes repository root"):
        chunk_file(repo_root, make_scanned_file("../outside.py"))


def test_returns_relative_paths(tmp_path: Path) -> None:
    package_dir = tmp_path / "package"
    package_dir.mkdir()
    write_lines(package_dir / "module.py", 2)

    chunks = chunk_file(tmp_path, make_scanned_file("package/module.py"))

    assert chunks[0].path == "package/module.py"
    assert not Path(chunks[0].path).is_absolute()


def test_is_deterministic_for_same_input(tmp_path: Path) -> None:
    file_path = tmp_path / "app.py"
    write_lines(file_path, 10)
    scanned_file = make_scanned_file("app.py")

    first_result = chunk_file(
        tmp_path,
        scanned_file,
        max_lines_per_chunk=4,
        overlap_lines=1,
    )
    second_result = chunk_file(
        tmp_path,
        scanned_file,
        max_lines_per_chunk=4,
        overlap_lines=1,
    )

    assert [chunk.model_dump() for chunk in first_result] == [
        chunk.model_dump() for chunk in second_result
    ]
