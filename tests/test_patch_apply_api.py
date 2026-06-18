from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from repopilot.llm import FakeLLMClient
from repopilot.main import app


def test_patch_apply_api_applies_approved_proposal(tmp_path: Path) -> None:
    target_file = _make_repo(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/patches/apply",
        json={
            "root_path": str(tmp_path),
            "proposal": _proposal(),
            "approved": True,
        },
    )

    assert response.status_code == 200
    assert target_file.read_text(encoding="utf-8") == "print('new')\n"


def test_patch_apply_api_response_includes_changed_file_count(
    tmp_path: Path,
) -> None:
    _make_repo(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/patches/apply",
        json={
            "root_path": str(tmp_path),
            "proposal": _proposal(),
            "approved": True,
        },
    )

    assert response.json()["changed_file_count"] == 1


def test_patch_apply_api_response_includes_file_path_and_changed_flag(
    tmp_path: Path,
) -> None:
    _make_repo(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/patches/apply",
        json={
            "root_path": str(tmp_path),
            "proposal": _proposal(),
            "approved": True,
        },
    )

    assert response.json()["applied_files"] == [
        {"path": "src/app.py", "changed": True}
    ]


def test_patch_apply_api_response_omits_old_and_new_content(
    tmp_path: Path,
) -> None:
    _make_repo(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/patches/apply",
        json={
            "root_path": str(tmp_path),
            "proposal": _proposal(),
            "approved": True,
        },
    )

    assert "old_content" not in response.text
    assert "new_content" not in response.text


def test_patch_apply_api_approved_false_returns_error_and_does_not_modify(
    tmp_path: Path,
) -> None:
    target_file = _make_repo(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/patches/apply",
        json={
            "root_path": str(tmp_path),
            "proposal": _proposal(),
            "approved": False,
        },
    )

    assert response.status_code == 400
    assert "explicitly approved" in response.json()["detail"]
    assert target_file.read_text(encoding="utf-8") == "print('old')\n"


def test_patch_apply_api_requires_approval_flag_on_proposal(
    tmp_path: Path,
) -> None:
    target_file = _make_repo(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/patches/apply",
        json={
            "root_path": str(tmp_path),
            "proposal": _proposal(requires_approval=False),
            "approved": True,
        },
    )

    assert response.status_code == 400
    assert "must require approval" in response.json()["detail"]
    assert target_file.read_text(encoding="utf-8") == "print('old')\n"


def test_patch_apply_api_content_mismatch_returns_400(tmp_path: Path) -> None:
    target_file = _make_repo(tmp_path)
    client = TestClient(app)
    proposal = _proposal(original_content="print('different')\n")

    response = client.post(
        "/patches/apply",
        json={
            "root_path": str(tmp_path),
            "proposal": proposal,
            "approved": True,
        },
    )

    assert response.status_code == 400
    assert "does not match proposal original_content" in response.json()["detail"]
    assert target_file.read_text(encoding="utf-8") == "print('old')\n"


def test_patch_apply_api_missing_root_returns_400(tmp_path: Path) -> None:
    client = TestClient(app)

    response = client.post(
        "/patches/apply",
        json={
            "root_path": str(tmp_path / "missing"),
            "proposal": _proposal(),
            "approved": True,
        },
    )

    assert response.status_code == 400
    assert "does not exist" in response.json()["detail"]


def test_patch_apply_api_blank_root_path_returns_validation_error() -> None:
    client = TestClient(app)

    response = client.post(
        "/patches/apply",
        json={
            "root_path": "   ",
            "proposal": _proposal(),
            "approved": True,
        },
    )

    assert response.status_code == 422


def test_patch_apply_api_requires_explicit_approved_field(
    tmp_path: Path,
) -> None:
    _make_repo(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/patches/apply",
        json={
            "root_path": str(tmp_path),
            "proposal": _proposal(),
        },
    )

    assert response.status_code == 422


def test_patch_apply_api_paths_remain_relative(tmp_path: Path) -> None:
    _make_repo(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/patches/apply",
        json={
            "root_path": str(tmp_path),
            "proposal": _proposal(),
            "approved": True,
        },
    )
    path = response.json()["applied_files"][0]["path"]

    assert not Path(path).is_absolute()
    assert str(tmp_path) not in response.text


def test_patch_apply_api_does_not_call_llms_commands_validation_or_self_correction(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _make_repo(tmp_path)

    def fail_generate(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("LLM client should not be called")

    def fail_run_command(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("run_command should not be called")

    def fail_validation_pipeline(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("apply_and_validate_patch should not be called")

    def fail_self_correction(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("self-correction should not be started")

    monkeypatch.setattr(FakeLLMClient, "generate", fail_generate)
    monkeypatch.setattr("repopilot.tools.commands.run_command", fail_run_command)
    monkeypatch.setattr(
        "repopilot.validation.pipeline.apply_and_validate_patch",
        fail_validation_pipeline,
    )
    monkeypatch.setattr(
        "repopilot.agent.orchestrator.run_self_correction_loop",
        fail_self_correction,
    )
    client = TestClient(app)

    response = client.post(
        "/patches/apply",
        json={
            "root_path": str(tmp_path),
            "proposal": _proposal(),
            "approved": True,
        },
    )

    assert response.status_code == 200


def test_patch_apply_api_is_deterministic_for_same_valid_apply_scenario(
    tmp_path: Path,
) -> None:
    first_root = tmp_path / "first"
    second_root = tmp_path / "second"
    _make_repo(first_root)
    _make_repo(second_root)
    client = TestClient(app)
    first_request = {
        "root_path": str(first_root),
        "proposal": _proposal(),
        "approved": True,
    }
    second_request = {
        "root_path": str(second_root),
        "proposal": _proposal(),
        "approved": True,
    }

    first = client.post("/patches/apply", json=first_request).json()
    second = client.post("/patches/apply", json=second_request).json()

    assert first == second


def test_patch_apply_api_failed_apply_does_not_partially_write_files(
    tmp_path: Path,
) -> None:
    source_dir = tmp_path / "src"
    source_dir.mkdir()
    app_file = source_dir / "app.py"
    utils_file = source_dir / "utils.py"
    app_file.write_bytes(b"print('old app')\n")
    utils_file.write_bytes(b"print('old utils')\n")
    client = TestClient(app)

    response = client.post(
        "/patches/apply",
        json={
            "root_path": str(tmp_path),
            "proposal": _multi_file_proposal_with_mismatch(),
            "approved": True,
        },
    )

    assert response.status_code == 400
    assert app_file.read_text(encoding="utf-8") == "print('old app')\n"
    assert utils_file.read_text(encoding="utf-8") == "print('old utils')\n"


def _make_repo(root_path: Path) -> Path:
    source_dir = root_path / "src"
    source_dir.mkdir(parents=True)
    target_file = source_dir / "app.py"
    target_file.write_bytes(b"print('old')\n")
    return target_file


def _proposal(
    *,
    original_content: str = "print('old')\n",
    proposed_content: str = "print('new')\n",
    requires_approval: bool = True,
) -> dict[str, object]:
    return {
        "summary": "Update app output.",
        "target_files": ["src/app.py"],
        "changes": [
            {
                "path": "src/app.py",
                "reason": "Approved test change.",
                "start_line": 1,
                "end_line": 1,
                "original_content": original_content,
                "proposed_content": proposed_content,
            }
        ],
        "risks": ["May affect app output."],
        "requires_approval": requires_approval,
    }


def _multi_file_proposal_with_mismatch() -> dict[str, object]:
    return {
        "summary": "Update two files.",
        "target_files": ["src/app.py", "src/utils.py"],
        "changes": [
            {
                "path": "src/app.py",
                "reason": "First change should not be partially written.",
                "start_line": 1,
                "end_line": 1,
                "original_content": "print('old app')\n",
                "proposed_content": "print('new app')\n",
            },
            {
                "path": "src/utils.py",
                "reason": "Second change has a content mismatch.",
                "start_line": 1,
                "end_line": 1,
                "original_content": "print('different utils')\n",
                "proposed_content": "print('new utils')\n",
            },
        ],
        "risks": ["May affect app output."],
        "requires_approval": True,
    }
