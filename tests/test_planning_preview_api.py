from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from repopilot.llm import FakeLLMClient
from repopilot.main import app


def test_planning_preview_returns_200_for_temp_repo(tmp_path: Path) -> None:
    _make_repo(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/repositories/plan-preview",
        json={"root_path": str(tmp_path), "issue": "Fix login validation"},
    )

    assert response.status_code == 200


def test_planning_preview_includes_root_name(tmp_path: Path) -> None:
    _make_repo(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/repositories/plan-preview",
        json={"root_path": str(tmp_path), "issue": "Fix login validation"},
    )

    assert response.json()["root_name"] == tmp_path.name


def test_planning_preview_includes_issue(tmp_path: Path) -> None:
    _make_repo(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/repositories/plan-preview",
        json={"root_path": str(tmp_path), "issue": "  Fix login validation  "},
    )

    assert response.json()["issue"] == "Fix login validation"


def test_planning_preview_includes_context_metadata(tmp_path: Path) -> None:
    _make_repo(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/repositories/plan-preview",
        json={"root_path": str(tmp_path), "issue": "Fix login validation"},
    )
    body = response.json()

    assert body["scanned_file_count"] == 2
    assert body["skipped_file_count"] == 1
    assert body["total_chunks"] == 2
    assert body["retrieved_count"] >= 1


def test_planning_preview_includes_plan_objective(tmp_path: Path) -> None:
    _make_repo(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/repositories/plan-preview",
        json={"root_path": str(tmp_path), "issue": "Fix login validation"},
    )

    assert response.json()["plan"]["objective"] == "Fix login validation"


def test_planning_preview_includes_relevant_files(tmp_path: Path) -> None:
    _make_repo(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/repositories/plan-preview",
        json={"root_path": str(tmp_path), "issue": "Fix login validation"},
    )

    assert response.json()["plan"]["relevant_files"] == ["src/auth.py"]


def test_planning_preview_includes_ordered_steps(tmp_path: Path) -> None:
    _make_repo(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/repositories/plan-preview",
        json={"root_path": str(tmp_path), "issue": "Fix login validation"},
    )
    steps = response.json()["plan"]["steps"]

    assert [step["order"] for step in steps] == list(range(1, len(steps) + 1))
    assert steps[0]["target_files"] == ["src/auth.py"]


def test_planning_preview_includes_confidence(tmp_path: Path) -> None:
    _make_repo(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/repositories/plan-preview",
        json={"root_path": str(tmp_path), "issue": "Fix login validation"},
    )

    confidence = response.json()["plan"]["confidence"]
    assert 0 <= confidence <= 1


def test_planning_preview_paths_are_relative(tmp_path: Path) -> None:
    _make_repo(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/repositories/plan-preview",
        json={"root_path": str(tmp_path), "issue": "Fix login validation"},
    )
    plan = response.json()["plan"]
    all_paths = [
        *plan["relevant_files"],
        *[
            path
            for step in plan["steps"]
            for path in step["target_files"]
        ],
    ]

    assert all(not Path(path).is_absolute() for path in all_paths)
    assert str(tmp_path) not in response.text


def test_planning_preview_blank_root_path_returns_validation_error() -> None:
    client = TestClient(app)

    response = client.post(
        "/repositories/plan-preview",
        json={"root_path": "   ", "issue": "Fix login validation"},
    )

    assert response.status_code == 422


def test_planning_preview_blank_issue_returns_validation_error(
    tmp_path: Path,
) -> None:
    _make_repo(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/repositories/plan-preview",
        json={"root_path": str(tmp_path), "issue": "   "},
    )

    assert response.status_code == 422


def test_planning_preview_invalid_top_k_returns_validation_error(
    tmp_path: Path,
) -> None:
    _make_repo(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/repositories/plan-preview",
        json={
            "root_path": str(tmp_path),
            "issue": "Fix login validation",
            "top_k": 0,
        },
    )

    assert response.status_code == 422


def test_planning_preview_missing_root_returns_400(tmp_path: Path) -> None:
    client = TestClient(app)

    response = client.post(
        "/repositories/plan-preview",
        json={
            "root_path": str(tmp_path / "missing"),
            "issue": "Fix login validation",
        },
    )

    assert response.status_code == 400
    assert "does not exist" in response.json()["detail"]


def test_planning_preview_does_not_call_llms_commands_or_patches(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    files = _make_repo(tmp_path)
    marker_content = files[0].read_text(encoding="utf-8")

    def fail_generate(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("LLM client should not be called")

    def fail_llm_plan(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("LLM planner should not be called")

    def fail_run_command(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("run_command should not be called")

    def fail_apply_patch(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("apply_patch_proposal should not be called")

    monkeypatch.setattr(FakeLLMClient, "generate", fail_generate)
    monkeypatch.setattr(
        "repopilot.planning.create_llm_implementation_plan",
        fail_llm_plan,
    )
    monkeypatch.setattr("repopilot.tools.commands.run_command", fail_run_command)
    monkeypatch.setattr(
        "repopilot.patching.applier.apply_patch_proposal",
        fail_apply_patch,
    )
    client = TestClient(app)

    response = client.post(
        "/repositories/plan-preview",
        json={"root_path": str(tmp_path), "issue": "Fix login validation"},
    )

    assert response.status_code == 200
    assert files[0].read_text(encoding="utf-8") == marker_content


def test_planning_preview_does_not_expose_hashes_or_file_contents(
    tmp_path: Path,
) -> None:
    _make_repo(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/repositories/plan-preview",
        json={"root_path": str(tmp_path), "issue": "Fix login validation"},
    )

    assert "sha256" not in response.text
    assert "SENSITIVE_FILE_CONTENT_SHOULD_NOT_LEAK" not in response.text


def test_planning_preview_is_deterministic_for_same_repo_and_issue(
    tmp_path: Path,
) -> None:
    _make_repo(tmp_path)
    client = TestClient(app)
    request_body = {
        "root_path": str(tmp_path),
        "issue": "Fix login validation",
        "top_k": 3,
    }

    first = client.post("/repositories/plan-preview", json=request_body).json()
    second = client.post("/repositories/plan-preview", json=request_body).json()

    assert first == second


def _make_repo(root_path: Path) -> list[Path]:
    source_dir = root_path / "src"
    source_dir.mkdir()
    auth_file = source_dir / "auth.py"
    billing_file = source_dir / "billing.py"
    auth_file.write_text(
        "def login_user(credentials):\n"
        "    SENSITIVE_FILE_CONTENT_SHOULD_NOT_LEAK = True\n"
        "    return bool(credentials)\n",
        encoding="utf-8",
    )
    billing_file.write_text(
        "def create_invoice():\n"
        "    return True\n",
        encoding="utf-8",
    )
    ignored_dir = root_path / "node_modules"
    ignored_dir.mkdir()
    (ignored_dir / "ignored.js").write_text(
        "const login = true;\n",
        encoding="utf-8",
    )
    (root_path / "image.png").write_bytes(b"not scanned")
    return [auth_file, billing_file]
