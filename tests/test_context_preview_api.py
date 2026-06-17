from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from repopilot.llm import FakeLLMClient
from repopilot.main import app


def test_context_preview_returns_200_for_temp_repo(tmp_path: Path) -> None:
    _make_repo(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/repositories/context-preview",
        json={"root_path": str(tmp_path), "query": "login"},
    )

    assert response.status_code == 200


def test_context_preview_includes_root_name(tmp_path: Path) -> None:
    _make_repo(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/repositories/context-preview",
        json={"root_path": str(tmp_path), "query": "login"},
    )

    assert response.json()["root_name"] == tmp_path.name


def test_context_preview_includes_total_chunks(tmp_path: Path) -> None:
    _make_repo(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/repositories/context-preview",
        json={"root_path": str(tmp_path), "query": "login"},
    )

    assert response.json()["total_chunks"] >= 2


def test_context_preview_includes_retrieved_count(tmp_path: Path) -> None:
    _make_repo(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/repositories/context-preview",
        json={"root_path": str(tmp_path), "query": "login"},
    )

    assert response.json()["retrieved_count"] == len(response.json()["chunks"])
    assert response.json()["retrieved_count"] >= 1


def test_context_preview_includes_chunk_previews(tmp_path: Path) -> None:
    _make_repo(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/repositories/context-preview",
        json={"root_path": str(tmp_path), "query": "login"},
    )

    chunk = response.json()["chunks"][0]
    assert chunk["path"] == "src/auth.py"
    assert chunk["language"] == "python"
    assert chunk["start_line"] == 1
    assert chunk["end_line"] >= 1
    assert chunk["score"] > 0
    assert "login" in chunk["matched_terms"]
    assert "login" in chunk["preview"]


def test_context_preview_truncates_preview_to_max_chars(tmp_path: Path) -> None:
    _make_repo(tmp_path, long_auth=True)
    client = TestClient(app)

    response = client.post(
        "/repositories/context-preview",
        json={
            "root_path": str(tmp_path),
            "query": "login",
            "max_preview_chars": 50,
        },
    )

    previews = [chunk["preview"] for chunk in response.json()["chunks"]]
    assert all(len(preview) <= 50 for preview in previews)


def test_context_preview_paths_are_relative(tmp_path: Path) -> None:
    _make_repo(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/repositories/context-preview",
        json={"root_path": str(tmp_path), "query": "login"},
    )

    assert all(
        not Path(chunk["path"]).is_absolute()
        for chunk in response.json()["chunks"]
    )


def test_context_preview_blank_root_path_returns_error() -> None:
    client = TestClient(app)

    response = client.post(
        "/repositories/context-preview",
        json={"root_path": "   ", "query": "login"},
    )

    assert response.status_code == 422


def test_context_preview_blank_query_returns_error(tmp_path: Path) -> None:
    _make_repo(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/repositories/context-preview",
        json={"root_path": str(tmp_path), "query": "   "},
    )

    assert response.status_code == 422


def test_context_preview_invalid_top_k_returns_validation_error(
    tmp_path: Path,
) -> None:
    _make_repo(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/repositories/context-preview",
        json={"root_path": str(tmp_path), "query": "login", "top_k": 0},
    )

    assert response.status_code == 422


def test_context_preview_invalid_max_preview_chars_returns_validation_error(
    tmp_path: Path,
) -> None:
    _make_repo(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/repositories/context-preview",
        json={
            "root_path": str(tmp_path),
            "query": "login",
            "max_preview_chars": 49,
        },
    )

    assert response.status_code == 422


def test_context_preview_missing_root_returns_400(tmp_path: Path) -> None:
    client = TestClient(app)

    response = client.post(
        "/repositories/context-preview",
        json={"root_path": str(tmp_path / "missing"), "query": "login"},
    )

    assert response.status_code == 400
    assert "does not exist" in response.json()["detail"]


def test_context_preview_does_not_call_llms_commands_or_patches(
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
        "/repositories/context-preview",
        json={"root_path": str(tmp_path), "query": "login"},
    )

    assert response.status_code == 200
    assert files[0].read_text(encoding="utf-8") == marker_content


def test_context_preview_does_not_expose_hashes(tmp_path: Path) -> None:
    _make_repo(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/repositories/context-preview",
        json={"root_path": str(tmp_path), "query": "login"},
    )

    assert "sha256" not in response.text


def test_context_preview_is_deterministic_for_same_repo_and_query(
    tmp_path: Path,
) -> None:
    _make_repo(tmp_path)
    client = TestClient(app)
    request_body = {
        "root_path": str(tmp_path),
        "query": "login",
        "top_k": 3,
        "max_preview_chars": 120,
    }

    first = client.post("/repositories/context-preview", json=request_body).json()
    second = client.post("/repositories/context-preview", json=request_body).json()

    assert first == second


def _make_repo(root_path: Path, *, long_auth: bool = False) -> list[Path]:
    source_dir = root_path / "src"
    source_dir.mkdir()
    auth_file = source_dir / "auth.py"
    billing_file = source_dir / "billing.py"
    auth_text = (
        "def login_user(credentials):\n"
        "    return bool(credentials)\n"
    )
    if long_auth:
        auth_text += "\n".join(
            f"# login validation note {index}"
            for index in range(1, 40)
        )
    billing_text = "def create_invoice():\n    return True\n"
    auth_file.write_text(auth_text, encoding="utf-8")
    billing_file.write_text(billing_text, encoding="utf-8")
    (root_path / "image.png").write_bytes(b"not scanned")
    return [auth_file, billing_file]
