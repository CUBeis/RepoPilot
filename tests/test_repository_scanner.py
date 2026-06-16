import hashlib
from pathlib import Path

import pytest

from repopilot.repository.scanner import RepositoryScanError, scan_repository


def test_scans_supported_files(tmp_path: Path) -> None:
    (tmp_path / "app.py").write_text("print('hello')\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("# RepoPilot\n", encoding="utf-8")

    result = scan_repository(tmp_path)

    assert result.root_name == tmp_path.name
    assert result.file_count == 2
    assert {file.path for file in result.files} == {"app.py", "README.md"}
    assert {file.language for file in result.files} == {"python", "markdown"}


def test_ignores_ignored_directories(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "config.py").write_text("ignored = True\n", encoding="utf-8")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "package.js").write_text(
        "console.log('ignored')\n",
        encoding="utf-8",
    )
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("print('kept')\n", encoding="utf-8")

    result = scan_repository(tmp_path)

    assert result.file_count == 1
    assert result.files[0].path == "src/main.py"


def test_skips_unsupported_files(tmp_path: Path) -> None:
    (tmp_path / "app.py").write_text("print('kept')\n", encoding="utf-8")
    (tmp_path / "image.png").write_bytes(b"not scanned")

    result = scan_repository(tmp_path)

    assert result.file_count == 1
    assert result.files[0].path == "app.py"
    assert result.skipped_count == 1


def test_skips_binary_files(tmp_path: Path) -> None:
    (tmp_path / "binary.txt").write_bytes(b"text\x00binary")

    result = scan_repository(tmp_path)

    assert result.file_count == 0
    assert result.skipped_count == 1


def test_returns_relative_paths(tmp_path: Path) -> None:
    package_dir = tmp_path / "package"
    package_dir.mkdir()
    (package_dir / "module.py").write_text("value = 1\n", encoding="utf-8")

    result = scan_repository(tmp_path)

    scanned_path = result.files[0].path
    assert scanned_path == "package/module.py"
    assert not Path(scanned_path).is_absolute()


def test_calculates_line_count(tmp_path: Path) -> None:
    (tmp_path / "notes.txt").write_text("one\ntwo\nthree", encoding="utf-8")

    result = scan_repository(tmp_path)

    assert result.files[0].line_count == 3


def test_calculates_sha256(tmp_path: Path) -> None:
    content = "print('hash me')\n"
    file_path = tmp_path / "hash.py"
    file_path.write_text(content, encoding="utf-8")

    result = scan_repository(tmp_path)

    assert result.files[0].sha256 == hashlib.sha256(file_path.read_bytes()).hexdigest()


def test_raises_clear_error_for_missing_path(tmp_path: Path) -> None:
    missing_path = tmp_path / "missing"

    with pytest.raises(RepositoryScanError, match="does not exist"):
        scan_repository(missing_path)


def test_raises_clear_error_when_path_is_file(tmp_path: Path) -> None:
    file_path = tmp_path / "file.py"
    file_path.write_text("print('not a directory')\n", encoding="utf-8")

    with pytest.raises(RepositoryScanError, match="not a directory"):
        scan_repository(file_path)


def test_respects_max_file_size(tmp_path: Path) -> None:
    (tmp_path / "large.py").write_text("0123456789", encoding="utf-8")

    result = scan_repository(tmp_path, max_file_size_bytes=5)

    assert result.file_count == 0
    assert result.skipped_count == 1
