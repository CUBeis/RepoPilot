from pathlib import Path

import pytest

from repopilot.tools import FileToolError, read_text_file, read_text_file_lines


def write_text(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")
    return path


def test_reads_whole_text_file(tmp_path: Path) -> None:
    write_text(tmp_path / "README.md", "# RepoPilot\nHello\n")

    result = read_text_file(tmp_path, "README.md")

    assert result.path == "README.md"
    assert result.start_line == 1
    assert result.end_line == 2
    assert result.content == "# RepoPilot\nHello\n"


def test_reads_specific_line_range(tmp_path: Path) -> None:
    write_text(tmp_path / "src" / "app.py", "line 1\nline 2\nline 3\nline 4\n")

    result = read_text_file_lines(tmp_path, "src/app.py", 2, 3)

    assert result.start_line == 2
    assert result.end_line == 3
    assert result.content == "line 2\nline 3"


def test_returns_total_lines_and_size_bytes(tmp_path: Path) -> None:
    file_path = write_text(tmp_path / "notes.txt", "one\ntwo\nthree")

    result = read_text_file(tmp_path, "notes.txt")

    assert result.total_lines == 3
    assert result.size_bytes == file_path.stat().st_size


def test_uses_relative_posix_output_paths(tmp_path: Path) -> None:
    write_text(tmp_path / "src" / "package" / "module.py", "value = 1\n")

    result = read_text_file(tmp_path, "src/package/module.py")

    assert result.path == "src/package/module.py"
    assert not Path(result.path).is_absolute()


def test_rejects_absolute_paths(tmp_path: Path) -> None:
    file_path = write_text(tmp_path / "secret.txt", "secret\n")

    with pytest.raises(FileToolError, match="absolute"):
        read_text_file(tmp_path, str(file_path))


def test_rejects_path_traversal_outside_repo(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    write_text(tmp_path / "secret.txt", "secret\n")

    with pytest.raises(FileToolError, match="escapes repository root"):
        read_text_file(repo_root, "../secret.txt")


def test_rejects_missing_files(tmp_path: Path) -> None:
    with pytest.raises(FileToolError, match="does not exist"):
        read_text_file(tmp_path, "missing.txt")


def test_rejects_directories(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()

    with pytest.raises(FileToolError, match="directory"):
        read_text_file(tmp_path, "src")


def test_rejects_invalid_line_ranges(tmp_path: Path) -> None:
    write_text(tmp_path / "notes.txt", "one\ntwo\n")

    with pytest.raises(FileToolError, match="start_line"):
        read_text_file_lines(tmp_path, "notes.txt", 0, 1)

    with pytest.raises(FileToolError, match="end_line"):
        read_text_file_lines(tmp_path, "notes.txt", 2, 1)

    with pytest.raises(FileToolError, match="exceeds total lines"):
        read_text_file_lines(tmp_path, "notes.txt", 1, 3)


def test_respects_max_bytes(tmp_path: Path) -> None:
    write_text(tmp_path / "large.txt", "0123456789")

    with pytest.raises(FileToolError, match="max_bytes"):
        read_text_file(tmp_path, "large.txt", max_bytes=5)


def test_respects_max_lines_for_whole_file_reads(tmp_path: Path) -> None:
    write_text(tmp_path / "many.txt", "one\ntwo\nthree\n")

    with pytest.raises(FileToolError, match="max_lines"):
        read_text_file(tmp_path, "many.txt", max_lines=2)


def test_rejects_binary_content(tmp_path: Path) -> None:
    (tmp_path / "binary.txt").write_bytes(b"text\x00binary")

    with pytest.raises(FileToolError, match="binary"):
        read_text_file(tmp_path, "binary.txt")


def test_rejects_invalid_utf8_content(tmp_path: Path) -> None:
    (tmp_path / "invalid.txt").write_bytes(b"\xff\xfe")

    with pytest.raises(FileToolError, match="valid UTF-8"):
        read_text_file(tmp_path, "invalid.txt")


def test_is_deterministic_for_same_input(tmp_path: Path) -> None:
    write_text(tmp_path / "notes.txt", "one\ntwo\nthree\n")

    first_result = read_text_file_lines(tmp_path, "notes.txt", 1, 2)
    second_result = read_text_file_lines(tmp_path, "notes.txt", 1, 2)

    assert first_result.model_dump() == second_result.model_dump()
