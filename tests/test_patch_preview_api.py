from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from repopilot.llm import FakeLLMClient
from repopilot.main import app


def test_patch_preview_returns_200_for_temp_repo(tmp_path: Path) -> None:
    _make_repo(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/repositories/patch-preview",
        json={"root_path": str(tmp_path), "issue": "Fix login validation"},
    )

    assert response.status_code == 200


def test_patch_preview_includes_root_name(tmp_path: Path) -> None:
    _make_repo(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/repositories/patch-preview",
        json={"root_path": str(tmp_path), "issue": "Fix login validation"},
    )

    assert response.json()["root_name"] == tmp_path.name


def test_patch_preview_includes_issue(tmp_path: Path) -> None:
    _make_repo(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/repositories/patch-preview",
        json={"root_path": str(tmp_path), "issue": "  Fix login validation  "},
    )

    assert response.json()["issue"] == "Fix login validation"


def test_patch_preview_includes_context_metadata(tmp_path: Path) -> None:
    _make_repo(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/repositories/patch-preview",
        json={"root_path": str(tmp_path), "issue": "Fix login validation"},
    )
    body = response.json()

    assert body["scanned_file_count"] == 2
    assert body["skipped_file_count"] == 1
    assert body["total_chunks"] == 2
    assert body["retrieved_count"] >= 1


def test_patch_preview_includes_plan(tmp_path: Path) -> None:
    _make_repo(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/repositories/patch-preview",
        json={"root_path": str(tmp_path), "issue": "Fix login validation"},
    )
    plan = response.json()["plan"]

    assert plan["objective"] == "Fix login validation"
    assert plan["relevant_files"] == ["src/auth.py"]
    assert plan["steps"][0]["order"] == 1
    assert 0 <= plan["confidence"] <= 1


def test_patch_preview_includes_proposal_summary(tmp_path: Path) -> None:
    _make_repo(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/repositories/patch-preview",
        json={"root_path": str(tmp_path), "issue": "Fix login validation"},
    )

    assert "approval-gated patch proposal" in response.json()["proposal"]["summary"]


def test_patch_preview_includes_target_files(tmp_path: Path) -> None:
    _make_repo(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/repositories/patch-preview",
        json={"root_path": str(tmp_path), "issue": "Fix login validation"},
    )

    assert response.json()["proposal"]["target_files"] == ["src/auth.py"]


def test_patch_preview_includes_change_previews(tmp_path: Path) -> None:
    _make_repo(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/repositories/patch-preview",
        json={"root_path": str(tmp_path), "issue": "Fix login validation"},
    )
    change = response.json()["proposal"]["changes"][0]

    assert change["path"] == "src/auth.py"
    assert "Planned step" in change["reason"]
    assert change["start_line"] == 1
    assert change["end_line"] >= 1
    assert "def login_user" in change["original_preview"]
    assert change["proposed_preview"] == change["original_preview"]


def test_patch_preview_requires_approval(tmp_path: Path) -> None:
    _make_repo(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/repositories/patch-preview",
        json={"root_path": str(tmp_path), "issue": "Fix login validation"},
    )

    assert response.json()["proposal"]["requires_approval"] is True


def test_patch_preview_truncates_change_previews(tmp_path: Path) -> None:
    _make_repo(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/repositories/patch-preview",
        json={
            "root_path": str(tmp_path),
            "issue": "Fix login validation",
            "max_preview_chars": 50,
        },
    )
    change = response.json()["proposal"]["changes"][0]

    assert len(change["original_preview"]) <= 50
    assert len(change["proposed_preview"]) <= 50


def test_patch_preview_paths_are_relative(tmp_path: Path) -> None:
    _make_repo(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/repositories/patch-preview",
        json={"root_path": str(tmp_path), "issue": "Fix login validation"},
    )
    body = response.json()
    all_paths = [
        *body["plan"]["relevant_files"],
        *[
            path
            for step in body["plan"]["steps"]
            for path in step["target_files"]
        ],
        *body["proposal"]["target_files"],
        *[change["path"] for change in body["proposal"]["changes"]],
    ]

    assert all(not Path(path).is_absolute() for path in all_paths)
    assert str(tmp_path) not in response.text


def test_patch_preview_blank_root_path_returns_validation_error() -> None:
    client = TestClient(app)

    response = client.post(
        "/repositories/patch-preview",
        json={"root_path": "   ", "issue": "Fix login validation"},
    )

    assert response.status_code == 422


def test_patch_preview_blank_issue_returns_validation_error(
    tmp_path: Path,
) -> None:
    _make_repo(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/repositories/patch-preview",
        json={"root_path": str(tmp_path), "issue": "   "},
    )

    assert response.status_code == 422


def test_patch_preview_invalid_top_k_returns_validation_error(
    tmp_path: Path,
) -> None:
    _make_repo(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/repositories/patch-preview",
        json={
            "root_path": str(tmp_path),
            "issue": "Fix login validation",
            "top_k": 0,
        },
    )

    assert response.status_code == 422


def test_patch_preview_invalid_max_preview_chars_returns_validation_error(
    tmp_path: Path,
) -> None:
    _make_repo(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/repositories/patch-preview",
        json={
            "root_path": str(tmp_path),
            "issue": "Fix login validation",
            "max_preview_chars": 49,
        },
    )

    assert response.status_code == 422


def test_patch_preview_missing_root_returns_400(tmp_path: Path) -> None:
    client = TestClient(app)

    response = client.post(
        "/repositories/patch-preview",
        json={
            "root_path": str(tmp_path / "missing"),
            "issue": "Fix login validation",
        },
    )

    assert response.status_code == 400
    assert "does not exist" in response.json()["detail"]


def test_patch_preview_does_not_call_llms_commands_or_apply_patches(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    files = _make_repo(tmp_path)
    marker_content = files[0].read_text(encoding="utf-8")

    def fail_generate(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("LLM client should not be called")

    def fail_llm_patch(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("LLM patch proposal should not be called")

    def fail_run_command(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("run_command should not be called")

    def fail_apply_patch(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("apply_patch_proposal should not be called")

    monkeypatch.setattr(FakeLLMClient, "generate", fail_generate)
    monkeypatch.setattr(
        "repopilot.patching.create_llm_patch_proposal",
        fail_llm_patch,
    )
    monkeypatch.setattr("repopilot.tools.commands.run_command", fail_run_command)
    monkeypatch.setattr(
        "repopilot.patching.applier.apply_patch_proposal",
        fail_apply_patch,
    )
    client = TestClient(app)

    response = client.post(
        "/repositories/patch-preview",
        json={"root_path": str(tmp_path), "issue": "Fix login validation"},
    )

    assert response.status_code == 200
    assert files[0].read_text(encoding="utf-8") == marker_content


def test_patch_preview_does_not_expose_hashes_or_unbounded_content(
    tmp_path: Path,
) -> None:
    _make_repo(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/repositories/patch-preview",
        json={
            "root_path": str(tmp_path),
            "issue": "Fix login validation",
            "max_preview_chars": 50,
        },
    )

    assert "sha256" not in response.text
    assert "TAIL_CONTENT_SHOULD_NOT_LEAK" not in response.text


def test_patch_preview_is_deterministic_for_same_repo_and_issue(
    tmp_path: Path,
) -> None:
    _make_repo(tmp_path)
    client = TestClient(app)
    request_body = {
        "root_path": str(tmp_path),
        "issue": "Fix login validation",
        "top_k": 3,
        "max_preview_chars": 120,
    }

    first = client.post("/repositories/patch-preview", json=request_body).json()
    second = client.post("/repositories/patch-preview", json=request_body).json()

    assert first == second


def _make_repo(root_path: Path) -> list[Path]:
    source_dir = root_path / "src"
    source_dir.mkdir()
    auth_file = source_dir / "auth.py"
    billing_file = source_dir / "billing.py"
    auth_file.write_text(
        "def login_user(credentials):\n"
        "    login_is_valid = bool(credentials)\n"
        "    return login_is_valid\n"
        "# " + ("padding " * 20) + "TAIL_CONTENT_SHOULD_NOT_LEAK\n",
        encoding="utf-8",
    )
    billing_file.write_text(
        "def create_invoice():\n"
        "    return True\n",
        encoding="utf-8",
    )
    (root_path / "image.png").write_bytes(b"not scanned")
    return [auth_file, billing_file]
