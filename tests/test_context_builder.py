from pathlib import Path

import pytest

from repopilot.context import build_repository_context
from repopilot.repository.scanner import RepositoryScanError


def write_text_file(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_scans_chunks_and_retrieves_in_one_call(tmp_path: Path) -> None:
    write_text_file(tmp_path / "src" / "auth.py", "def login_user():\n    pass\n")
    write_text_file(
        tmp_path / "src" / "billing.py",
        "def create_invoice():\n    pass\n",
    )

    context = build_repository_context(tmp_path, "login user")

    assert context.root_name == tmp_path.name
    assert context.scanned_file_count == 2
    assert context.total_chunks == 2
    assert len(context.retrieved_chunks) == 1
    assert context.retrieved_chunks[0].chunk.path == "src/auth.py"


def test_returns_empty_retrieved_chunks_for_empty_query(tmp_path: Path) -> None:
    write_text_file(tmp_path / "src" / "auth.py", "def login_user():\n    pass\n")

    context = build_repository_context(tmp_path, "  ")

    assert context.scanned_file_count == 1
    assert context.total_chunks == 1
    assert context.retrieved_chunks == []


def test_includes_scan_summary_values(tmp_path: Path) -> None:
    first_file = write_text_file(tmp_path / "src" / "auth.py", "auth\n")
    second_file = write_text_file(tmp_path / "README.md", "# Docs\n")
    (tmp_path / "logo.png").write_bytes(b"unsupported")

    context = build_repository_context(tmp_path, "auth")

    assert context.scanned_file_count == 2
    assert context.total_size_bytes == (
        first_file.stat().st_size + second_file.stat().st_size
    )
    assert context.skipped_file_count == 1


def test_includes_total_chunk_count(tmp_path: Path) -> None:
    text = "\n".join(f"line {line_number}" for line_number in range(1, 8))
    write_text_file(tmp_path / "src" / "auth.py", text)

    context = build_repository_context(
        tmp_path,
        "line",
        max_lines_per_chunk=3,
        overlap_lines=1,
    )

    assert context.total_chunks == 3


def test_respects_top_k(tmp_path: Path) -> None:
    for index in range(3):
        write_text_file(tmp_path / f"file_{index}.py", "def query_match():\n    pass\n")

    context = build_repository_context(tmp_path, "query", top_k=2)

    assert len(context.retrieved_chunks) == 2


def test_is_deterministic_for_same_repo_and_query(tmp_path: Path) -> None:
    write_text_file(tmp_path / "b.py", "shared\n")
    write_text_file(tmp_path / "a.py", "shared\n")

    first_context = build_repository_context(tmp_path, "shared")
    second_context = build_repository_context(tmp_path, "shared")

    assert first_context.model_dump() == second_context.model_dump()


def test_propagates_clear_error_for_invalid_path(tmp_path: Path) -> None:
    missing_path = tmp_path / "missing"

    with pytest.raises(RepositoryScanError, match="does not exist"):
        build_repository_context(missing_path, "query")


def test_works_with_nested_files_and_relative_paths(tmp_path: Path) -> None:
    write_text_file(
        tmp_path / "src" / "features" / "auth" / "routes.py",
        "def login_route():\n    pass\n",
    )

    context = build_repository_context(tmp_path, "login route")

    assert len(context.retrieved_chunks) == 1
    assert context.retrieved_chunks[0].chunk.path == "src/features/auth/routes.py"
    assert not Path(context.retrieved_chunks[0].chunk.path).is_absolute()
