import sys
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from repopilot.llm import FakeLLMClient
from repopilot.main import app
from repopilot.tools import CommandToolError
from repopilot.tools.models import CommandResult


def test_repair_apply_api_applies_approved_repair_without_validation(
    tmp_path: Path,
) -> None:
    target_file = _make_repo(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/repairs/apply-approved",
        json=_request_body(tmp_path),
    )

    assert response.status_code == 200
    assert target_file.read_text(encoding="utf-8") == "print('new')\n"


def test_repair_apply_api_response_includes_changed_file_count(
    tmp_path: Path,
) -> None:
    _make_repo(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/repairs/apply-approved",
        json=_request_body(tmp_path),
    )

    assert response.json()["changed_file_count"] == 1


def test_repair_apply_api_response_includes_applied_files(
    tmp_path: Path,
) -> None:
    _make_repo(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/repairs/apply-approved",
        json=_request_body(tmp_path),
    )

    assert response.json()["applied_files"] == [
        {"path": "src/app.py", "changed": True}
    ]


def test_repair_apply_api_validation_is_none_when_not_requested(
    tmp_path: Path,
) -> None:
    _make_repo(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/repairs/apply-approved",
        json=_request_body(tmp_path),
    )

    assert response.json()["validation"] is None


def test_repair_apply_api_approved_false_errors_and_does_not_modify(
    tmp_path: Path,
) -> None:
    target_file = _make_repo(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/repairs/apply-approved",
        json=_request_body(tmp_path, approved=False),
    )

    assert response.status_code == 400
    assert "explicitly approved" in response.json()["detail"]
    assert target_file.read_text(encoding="utf-8") == "print('old')\n"


def test_repair_apply_api_requires_proposal_approval_flag(
    tmp_path: Path,
) -> None:
    target_file = _make_repo(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/repairs/apply-approved",
        json=_request_body(
            tmp_path,
            repair_proposal=_repair_proposal(requires_approval=False),
        ),
    )

    assert response.status_code == 400
    assert "must require approval" in response.json()["detail"]
    assert target_file.read_text(encoding="utf-8") == "print('old')\n"


def test_repair_apply_api_content_mismatch_returns_400(
    tmp_path: Path,
) -> None:
    target_file = _make_repo(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/repairs/apply-approved",
        json=_request_body(
            tmp_path,
            repair_proposal=_repair_proposal(
                original_content="print('different')\n"
            ),
        ),
    )

    assert response.status_code == 400
    assert "does not match proposal original_content" in response.json()["detail"]
    assert target_file.read_text(encoding="utf-8") == "print('old')\n"


def test_repair_apply_api_missing_root_returns_400(tmp_path: Path) -> None:
    client = TestClient(app)

    response = client.post(
        "/repairs/apply-approved",
        json=_request_body(tmp_path / "missing"),
    )

    assert response.status_code == 400
    assert "does not exist" in response.json()["detail"]


def test_repair_apply_api_response_omits_old_and_new_content(
    tmp_path: Path,
) -> None:
    _make_repo(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/repairs/apply-approved",
        json=_request_body(tmp_path),
    )

    assert "old_content" not in response.text
    assert "new_content" not in response.text


def test_repair_apply_api_paths_remain_relative(tmp_path: Path) -> None:
    _make_repo(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/repairs/apply-approved",
        json=_request_body(tmp_path),
    )
    path = response.json()["applied_files"][0]["path"]

    assert not Path(path).is_absolute()
    assert str(tmp_path) not in response.text


def test_repair_apply_api_run_validation_true_applies_and_runs_command(
    tmp_path: Path,
) -> None:
    target_file = _make_repo(tmp_path)
    command = _python_command("print('repair validation ok')")
    client = TestClient(app)

    response = client.post(
        "/repairs/apply-approved",
        json=_request_body(
            tmp_path,
            run_validation=True,
            validation_commands=[command],
        ),
    )

    assert response.status_code == 200
    assert target_file.read_text(encoding="utf-8") == "print('new')\n"
    assert response.json()["validation"]["checks"][0]["stdout_preview"].strip() == (
        "repair validation ok"
    )


def test_repair_apply_api_run_validation_true_returns_checks_and_passed(
    tmp_path: Path,
) -> None:
    _make_repo(tmp_path)
    command = _python_command("print('ok')")
    client = TestClient(app)

    response = client.post(
        "/repairs/apply-approved",
        json=_request_body(
            tmp_path,
            run_validation=True,
            validation_commands=[command],
        ),
    )
    validation = response.json()["validation"]

    assert validation["passed"] is True
    assert validation["checks"][0]["command"] == command
    assert validation["checks"][0]["passed"] is True


def test_repair_apply_api_validation_commands_are_exact_allowlist(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _make_repo(tmp_path)
    command = ["custom-repair-validator", "--check"]
    calls: list[tuple[list[str], list[list[str]]]] = []

    def fake_run_command(*args: Any, **kwargs: Any) -> CommandResult:
        calls.append((args[1], kwargs["allowed_commands"]))
        return _command_result(command, return_code=0)

    monkeypatch.setattr("repopilot.validation.pipeline.run_command", fake_run_command)
    client = TestClient(app)

    response = client.post(
        "/repairs/apply-approved",
        json=_request_body(
            tmp_path,
            run_validation=True,
            validation_commands=[command],
        ),
    )

    assert response.status_code == 200
    assert calls == [(command, [command])]


def test_repair_apply_api_maps_command_tool_errors_to_400(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _make_repo(tmp_path)

    def fake_apply_and_validate(*args: Any, **kwargs: Any) -> None:
        raise CommandToolError("Command is not allowlisted: unsafe")

    monkeypatch.setattr(
        "repopilot.api.repair_apply.apply_and_validate_patch",
        fake_apply_and_validate,
    )
    client = TestClient(app)

    response = client.post(
        "/repairs/apply-approved",
        json=_request_body(
            tmp_path,
            run_validation=True,
            validation_commands=[["unsafe"]],
        ),
    )

    assert response.status_code == 400
    assert "not allowlisted" in response.json()["detail"]


def test_repair_apply_api_invalid_timeout_returns_validation_error(
    tmp_path: Path,
) -> None:
    _make_repo(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/repairs/apply-approved",
        json=_request_body(tmp_path, timeout_seconds=0),
    )

    assert response.status_code == 422


def test_repair_apply_api_invalid_validation_commands_returns_error(
    tmp_path: Path,
) -> None:
    _make_repo(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/repairs/apply-approved",
        json=_request_body(tmp_path, validation_commands=[]),
    )

    assert response.status_code == 422


def test_repair_apply_api_blank_root_path_returns_validation_error() -> None:
    client = TestClient(app)

    response = client.post(
        "/repairs/apply-approved",
        json={
            "root_path": "   ",
            "repair_proposal": _repair_proposal(),
            "approved": True,
        },
    )

    assert response.status_code == 422


def test_repair_apply_api_requires_explicit_approved_field(
    tmp_path: Path,
) -> None:
    _make_repo(tmp_path)
    body = _request_body(tmp_path)
    body.pop("approved")
    client = TestClient(app)

    response = client.post("/repairs/apply-approved", json=body)

    assert response.status_code == 422


def test_repair_apply_api_does_not_run_commands_when_validation_is_false(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _make_repo(tmp_path)

    def fail_run_command(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("run_command should not be called")

    monkeypatch.setattr("repopilot.validation.pipeline.run_command", fail_run_command)
    client = TestClient(app)

    response = client.post(
        "/repairs/apply-approved",
        json=_request_body(tmp_path, validation_commands=[["unused"]]),
    )

    assert response.status_code == 200


def test_repair_apply_api_does_not_call_llms_or_generate_repairs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _make_repo(tmp_path)
    command = _python_command("print('ok')")

    def fail_generate(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("LLM client should not be called")

    def fail_repair_generation(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("repair generation should not be called")

    def fail_repair_workflow(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("repair approval workflow should not be called")

    def fail_self_correction(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("self-correction should not be started")

    def fail_failure_analysis(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("failure analyzer should not be called")

    monkeypatch.setattr(FakeLLMClient, "generate", fail_generate)
    monkeypatch.setattr(
        "repopilot.agent.repair.create_llm_repair_proposal",
        fail_repair_generation,
    )
    monkeypatch.setattr(
        "repopilot.agent.repair_workflow.prepare_repair_for_approval",
        fail_repair_workflow,
    )
    monkeypatch.setattr(
        "repopilot.agent.orchestrator.run_self_correction_loop",
        fail_self_correction,
    )
    monkeypatch.setattr(
        "repopilot.validation.failure_analysis.analyze_validation_result",
        fail_failure_analysis,
    )
    client = TestClient(app)

    response = client.post(
        "/repairs/apply-approved",
        json=_request_body(
            tmp_path,
            run_validation=True,
            validation_commands=[command],
        ),
    )

    assert response.status_code == 200


def test_repair_apply_api_failed_apply_does_not_partially_write_files(
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
        "/repairs/apply-approved",
        json=_request_body(
            tmp_path,
            repair_proposal=_multi_file_repair_proposal_with_mismatch(),
        ),
    )

    assert response.status_code == 400
    assert app_file.read_text(encoding="utf-8") == "print('old app')\n"
    assert utils_file.read_text(encoding="utf-8") == "print('old utils')\n"


def test_repair_apply_api_is_deterministic_for_same_valid_scenario(
    tmp_path: Path,
) -> None:
    first_root = tmp_path / "first"
    second_root = tmp_path / "second"
    _make_repo(first_root)
    _make_repo(second_root)
    client = TestClient(app)

    first = client.post(
        "/repairs/apply-approved",
        json=_request_body(first_root),
    ).json()
    second = client.post(
        "/repairs/apply-approved",
        json=_request_body(second_root),
    ).json()

    assert first == second


def _make_repo(root_path: Path) -> Path:
    source_dir = root_path / "src"
    source_dir.mkdir(parents=True)
    target_file = source_dir / "app.py"
    target_file.write_bytes(b"print('old')\n")
    return target_file


def _request_body(
    root_path: Path,
    *,
    repair_proposal: dict[str, object] | None = None,
    approved: bool = True,
    run_validation: bool = False,
    validation_commands: list[list[str]] | None = None,
    timeout_seconds: int = 30,
) -> dict[str, object]:
    request_body: dict[str, object] = {
        "root_path": str(root_path),
        "repair_proposal": (
            _repair_proposal() if repair_proposal is None else repair_proposal
        ),
        "approved": approved,
        "run_validation": run_validation,
        "timeout_seconds": timeout_seconds,
    }
    if validation_commands is not None:
        request_body["validation_commands"] = validation_commands
    return request_body


def _repair_proposal(
    *,
    original_content: str = "print('old')\n",
    proposed_content: str = "print('new')\n",
    requires_approval: bool = True,
) -> dict[str, object]:
    return {
        "summary": "Repair app output.",
        "target_files": ["src/app.py"],
        "changes": [
            {
                "path": "src/app.py",
                "reason": "Approved repair change.",
                "start_line": 1,
                "end_line": 1,
                "original_content": original_content,
                "proposed_content": proposed_content,
            }
        ],
        "risks": ["May affect app output."],
        "requires_approval": requires_approval,
    }


def _multi_file_repair_proposal_with_mismatch() -> dict[str, object]:
    return {
        "summary": "Repair two files.",
        "target_files": ["src/app.py", "src/utils.py"],
        "changes": [
            {
                "path": "src/app.py",
                "reason": "First repair should not be partially written.",
                "start_line": 1,
                "end_line": 1,
                "original_content": "print('old app')\n",
                "proposed_content": "print('new app')\n",
            },
            {
                "path": "src/utils.py",
                "reason": "Second repair has a content mismatch.",
                "start_line": 1,
                "end_line": 1,
                "original_content": "print('different utils')\n",
                "proposed_content": "print('new utils')\n",
            },
        ],
        "risks": ["May affect app output."],
        "requires_approval": True,
    }


def _python_command(code: str) -> list[str]:
    return [sys.executable, "-c", code]


def _command_result(command: list[str], *, return_code: int) -> CommandResult:
    return CommandResult(
        command=command,
        return_code=return_code,
        stdout="stdout",
        stderr="stderr",
        timed_out=False,
    )
