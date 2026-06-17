from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from repopilot.llm import FakeLLMClient
from repopilot.main import app


def test_repository_scan_summary_returns_200_for_temp_repo(tmp_path: Path) -> None:
    _make_repo(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/repositories/scan-summary",
        json={"root_path": str(tmp_path)},
    )

    assert response.status_code == 200


def test_repository_scan_summary_includes_root_name(tmp_path: Path) -> None:
    _make_repo(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/repositories/scan-summary",
        json={"root_path": str(tmp_path)},
    )

    assert response.json()["root_name"] == tmp_path.name


def test_repository_scan_summary_includes_file_count(tmp_path: Path) -> None:
    _make_repo(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/repositories/scan-summary",
        json={"root_path": str(tmp_path)},
    )

    assert response.json()["file_count"] == 2


def test_repository_scan_summary_includes_total_size_bytes(tmp_path: Path) -> None:
    files = _make_repo(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/repositories/scan-summary",
        json={"root_path": str(tmp_path)},
    )

    expected_size = sum(path.stat().st_size for path in files)
    assert response.json()["total_size_bytes"] == expected_size


def test_repository_scan_summary_includes_skipped_count(tmp_path: Path) -> None:
    _make_repo(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/repositories/scan-summary",
        json={"root_path": str(tmp_path)},
    )

    assert response.json()["skipped_count"] == 1


def test_repository_scan_summary_includes_relative_file_summaries(
    tmp_path: Path,
) -> None:
    _make_repo(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/repositories/scan-summary",
        json={"root_path": str(tmp_path)},
    )

    files = response.json()["files"]
    paths = {file["path"] for file in files}
    assert paths == {"README.md", "src/app.py"}
    assert all(not Path(file["path"]).is_absolute() for file in files)
    assert files[0].keys() == {
        "path",
        "language",
        "extension",
        "size_bytes",
        "line_count",
    }


def test_repository_scan_summary_does_not_include_sha256(tmp_path: Path) -> None:
    _make_repo(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/repositories/scan-summary",
        json={"root_path": str(tmp_path)},
    )

    assert "sha256" not in response.json()["files"][0]


def test_repository_scan_summary_missing_root_returns_400(tmp_path: Path) -> None:
    client = TestClient(app)

    response = client.post(
        "/repositories/scan-summary",
        json={"root_path": str(tmp_path / "missing")},
    )

    assert response.status_code == 400
    assert "does not exist" in response.json()["detail"]


def test_repository_scan_summary_non_directory_root_returns_400(
    tmp_path: Path,
) -> None:
    file_path = tmp_path / "not-a-directory.py"
    file_path.write_text("print('nope')\n", encoding="utf-8")
    client = TestClient(app)

    response = client.post(
        "/repositories/scan-summary",
        json={"root_path": str(file_path)},
    )

    assert response.status_code == 400
    assert "not a directory" in response.json()["detail"]


def test_repository_scan_summary_empty_root_path_returns_error() -> None:
    client = TestClient(app)

    response = client.post(
        "/repositories/scan-summary",
        json={"root_path": "   "},
    )

    assert response.status_code in {400, 422}


def test_repository_scan_summary_does_not_call_llms_commands_or_patches(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    files = _make_repo(tmp_path)
    marker_content = files[0].read_text(encoding="utf-8")

    def fail_generate(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("LLM client should not be called")

    def fail_run_command(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("run_command should not be called")

    def fail_apply_patch(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("apply_patch_proposal should not be called")

    monkeypatch.setattr(FakeLLMClient, "generate", fail_generate)
    monkeypatch.setattr("repopilot.tools.commands.run_command", fail_run_command)
    monkeypatch.setattr(
        "repopilot.patching.applier.apply_patch_proposal",
        fail_apply_patch,
    )
    client = TestClient(app)

    response = client.post(
        "/repositories/scan-summary",
        json={"root_path": str(tmp_path)},
    )

    assert response.status_code == 200
    assert files[0].read_text(encoding="utf-8") == marker_content


def test_repository_scan_summary_is_deterministic(tmp_path: Path) -> None:
    _make_repo(tmp_path)
    client = TestClient(app)

    first = client.post(
        "/repositories/scan-summary",
        json={"root_path": str(tmp_path)},
    ).json()
    second = client.post(
        "/repositories/scan-summary",
        json={"root_path": str(tmp_path)},
    ).json()

    assert first == second


def _make_repo(root_path: Path) -> list[Path]:
    source_dir = root_path / "src"
    source_dir.mkdir()
    app_file = source_dir / "app.py"
    readme_file = root_path / "README.md"
    app_file.write_text("print('hello')\n", encoding="utf-8")
    readme_file.write_text("# Demo\n", encoding="utf-8")
    (root_path / "image.png").write_bytes(b"not scanned")
    return [app_file, readme_file]
