import sys
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from repopilot.llm import FakeLLMClient
from repopilot.main import app
from repopilot.patching.models import PatchAppliedFile, PatchApplyResult
from repopilot.tools import CommandToolError
from repopilot.tools.models import CommandResult
from repopilot.validation.models import PatchValidationResult, ValidationCheck


def test_apply_validate_api_applies_approved_proposal_and_runs_command(
    tmp_path: Path,
) -> None:
    target_file = _make_repo(tmp_path)
    command = _python_command("print('validation ok')")
    client = TestClient(app)

    response = client.post(
        "/patches/apply-and-validate",
        json=_request_body(tmp_path, validation_commands=[command]),
    )

    assert response.status_code == 200
    assert target_file.read_text(encoding="utf-8") == "print('new')\n"
    assert response.json()["checks"][0]["stdout_preview"].strip() == "validation ok"


def test_apply_validate_api_response_includes_changed_file_count(
    tmp_path: Path,
) -> None:
    _make_repo(tmp_path)
    command = _python_command("print('ok')")
    client = TestClient(app)

    response = client.post(
        "/patches/apply-and-validate",
        json=_request_body(tmp_path, validation_commands=[command]),
    )

    assert response.json()["changed_file_count"] == 1


def test_apply_validate_api_response_includes_applied_files(
    tmp_path: Path,
) -> None:
    _make_repo(tmp_path)
    command = _python_command("print('ok')")
    client = TestClient(app)

    response = client.post(
        "/patches/apply-and-validate",
        json=_request_body(tmp_path, validation_commands=[command]),
    )

    assert response.json()["applied_files"] == [
        {"path": "src/app.py", "changed": True}
    ]


def test_apply_validate_api_response_includes_validation_checks(
    tmp_path: Path,
) -> None:
    _make_repo(tmp_path)
    command = _python_command("print('ok')")
    client = TestClient(app)

    response = client.post(
        "/patches/apply-and-validate",
        json=_request_body(tmp_path, validation_commands=[command]),
    )
    check = response.json()["checks"][0]

    assert check["name"] == " ".join(command)
    assert check["command"] == command
    assert check["return_code"] == 0
    assert check["timed_out"] is False
    assert check["passed"] is True


def test_apply_validate_api_passed_true_when_command_succeeds(
    tmp_path: Path,
) -> None:
    _make_repo(tmp_path)
    command = _python_command("print('ok')")
    client = TestClient(app)

    response = client.post(
        "/patches/apply-and-validate",
        json=_request_body(tmp_path, validation_commands=[command]),
    )

    assert response.json()["passed"] is True


def test_apply_validate_api_passed_false_when_command_fails(
    tmp_path: Path,
) -> None:
    _make_repo(tmp_path)
    command = _python_command("import sys; print('failed'); sys.exit(7)")
    client = TestClient(app)

    response = client.post(
        "/patches/apply-and-validate",
        json=_request_body(tmp_path, validation_commands=[command]),
    )

    assert response.status_code == 200
    assert response.json()["passed"] is False
    assert response.json()["checks"][0]["return_code"] == 7
    assert response.json()["checks"][0]["passed"] is False


def test_apply_validate_api_bounds_stdout_and_stderr_previews(
    tmp_path: Path,
) -> None:
    _make_repo(tmp_path)
    command = _python_command(
        "import sys; print('x' * 2500); print('e' * 2500, file=sys.stderr)"
    )
    client = TestClient(app)

    response = client.post(
        "/patches/apply-and-validate",
        json=_request_body(tmp_path, validation_commands=[command]),
    )
    check = response.json()["checks"][0]

    assert len(check["stdout_preview"]) == 2000
    assert len(check["stderr_preview"]) == 2000


def test_apply_validate_api_response_omits_old_and_new_content(
    tmp_path: Path,
) -> None:
    _make_repo(tmp_path)
    command = _python_command("print('ok')")
    client = TestClient(app)

    response = client.post(
        "/patches/apply-and-validate",
        json=_request_body(tmp_path, validation_commands=[command]),
    )

    assert "old_content" not in response.text
    assert "new_content" not in response.text


def test_apply_validate_api_approved_false_returns_error_and_does_not_modify(
    tmp_path: Path,
) -> None:
    target_file = _make_repo(tmp_path)
    command = _python_command("print('ok')")
    client = TestClient(app)

    response = client.post(
        "/patches/apply-and-validate",
        json=_request_body(
            tmp_path,
            approved=False,
            validation_commands=[command],
        ),
    )

    assert response.status_code == 400
    assert "explicitly approved" in response.json()["detail"]
    assert target_file.read_text(encoding="utf-8") == "print('old')\n"


def test_apply_validate_api_content_mismatch_returns_400(
    tmp_path: Path,
) -> None:
    target_file = _make_repo(tmp_path)
    command = _python_command("print('ok')")
    client = TestClient(app)

    response = client.post(
        "/patches/apply-and-validate",
        json=_request_body(
            tmp_path,
            proposal=_proposal(original_content="print('different')\n"),
            validation_commands=[command],
        ),
    )

    assert response.status_code == 400
    assert "does not match proposal original_content" in response.json()["detail"]
    assert target_file.read_text(encoding="utf-8") == "print('old')\n"


def test_apply_validate_api_missing_root_returns_400(tmp_path: Path) -> None:
    command = _python_command("print('ok')")
    client = TestClient(app)

    response = client.post(
        "/patches/apply-and-validate",
        json=_request_body(tmp_path / "missing", validation_commands=[command]),
    )

    assert response.status_code == 400
    assert "does not exist" in response.json()["detail"]


def test_apply_validate_api_invalid_timeout_returns_validation_error(
    tmp_path: Path,
) -> None:
    _make_repo(tmp_path)
    command = _python_command("print('ok')")
    client = TestClient(app)

    response = client.post(
        "/patches/apply-and-validate",
        json=_request_body(
            tmp_path,
            validation_commands=[command],
            timeout_seconds=0,
        ),
    )

    assert response.status_code == 422


def test_apply_validate_api_invalid_validation_commands_returns_error(
    tmp_path: Path,
) -> None:
    _make_repo(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/patches/apply-and-validate",
        json=_request_body(tmp_path, validation_commands=[]),
    )

    assert response.status_code == 422


def test_apply_validate_api_disallowed_command_errors_become_400(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _make_repo(tmp_path)
    command = _python_command("print('ok')")

    def fake_apply_and_validate(*args: Any, **kwargs: Any) -> PatchValidationResult:
        raise CommandToolError("Command is not allowlisted: unsafe")

    monkeypatch.setattr(
        "repopilot.api.validation.apply_and_validate_patch",
        fake_apply_and_validate,
    )
    client = TestClient(app)

    response = client.post(
        "/patches/apply-and-validate",
        json=_request_body(tmp_path, validation_commands=[command]),
    )

    assert response.status_code == 400
    assert "not allowlisted" in response.json()["detail"]


def test_apply_validate_api_uses_requested_commands_as_exact_allowlist(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _make_repo(tmp_path)
    command = ["custom-validator", "--check"]
    calls: list[tuple[list[str], list[list[str]]]] = []

    def fake_run_command(*args: Any, **kwargs: Any) -> CommandResult:
        calls.append((args[1], kwargs["allowed_commands"]))
        return _command_result(command, return_code=0)

    monkeypatch.setattr("repopilot.validation.pipeline.run_command", fake_run_command)
    client = TestClient(app)

    response = client.post(
        "/patches/apply-and-validate",
        json=_request_body(tmp_path, validation_commands=[command]),
    )

    assert response.status_code == 200
    assert calls == [(command, [command])]


def test_apply_validate_api_omitted_commands_use_pipeline_default(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _make_repo(tmp_path)
    seen_validation_commands: list[list[str]] | None = [["unexpected"]]

    def fake_apply_and_validate(*args: Any, **kwargs: Any) -> PatchValidationResult:
        nonlocal seen_validation_commands
        seen_validation_commands = kwargs["validation_commands"]
        return _validation_result()

    monkeypatch.setattr(
        "repopilot.api.validation.apply_and_validate_patch",
        fake_apply_and_validate,
    )
    client = TestClient(app)

    response = client.post(
        "/patches/apply-and-validate",
        json=_request_body(tmp_path, validation_commands=None),
    )

    assert response.status_code == 200
    assert seen_validation_commands is None


def test_apply_validate_api_does_not_call_llms_repairs_self_correction_or_analysis(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _make_repo(tmp_path)
    command = _python_command("print('ok')")

    def fail_generate(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("LLM client should not be called")

    def fail_repair(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("repair generation should not be called")

    def fail_self_correction(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("self-correction should not be started")

    def fail_failure_analysis(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("failure analyzer should not be called")

    monkeypatch.setattr(FakeLLMClient, "generate", fail_generate)
    monkeypatch.setattr(
        "repopilot.agent.repair.create_llm_repair_proposal",
        fail_repair,
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
        "/patches/apply-and-validate",
        json=_request_body(tmp_path, validation_commands=[command]),
    )

    assert response.status_code == 200


def test_apply_validate_api_paths_remain_relative(tmp_path: Path) -> None:
    _make_repo(tmp_path)
    command = _python_command("print('ok')")
    client = TestClient(app)

    response = client.post(
        "/patches/apply-and-validate",
        json=_request_body(tmp_path, validation_commands=[command]),
    )
    path = response.json()["applied_files"][0]["path"]

    assert not Path(path).is_absolute()
    assert str(tmp_path) not in response.text


def test_apply_validate_api_failed_apply_does_not_partially_write_files(
    tmp_path: Path,
) -> None:
    source_dir = tmp_path / "src"
    source_dir.mkdir()
    app_file = source_dir / "app.py"
    utils_file = source_dir / "utils.py"
    app_file.write_bytes(b"print('old app')\n")
    utils_file.write_bytes(b"print('old utils')\n")
    command = _python_command("print('ok')")
    client = TestClient(app)

    response = client.post(
        "/patches/apply-and-validate",
        json=_request_body(
            tmp_path,
            proposal=_multi_file_proposal_with_mismatch(),
            validation_commands=[command],
        ),
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


def _request_body(
    root_path: Path,
    *,
    proposal: dict[str, object] | None = None,
    approved: bool = True,
    validation_commands: list[list[str]] | None = None,
    timeout_seconds: int = 30,
) -> dict[str, object]:
    request_body: dict[str, object] = {
        "root_path": str(root_path),
        "proposal": _proposal() if proposal is None else proposal,
        "approved": approved,
        "timeout_seconds": timeout_seconds,
    }
    if validation_commands is not None:
        request_body["validation_commands"] = validation_commands
    return request_body


def _proposal(
    *,
    original_content: str = "print('old')\n",
    proposed_content: str = "print('new')\n",
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
        "requires_approval": True,
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


def _python_command(code: str) -> list[str]:
    return [sys.executable, "-c", code]


def _validation_result() -> PatchValidationResult:
    return PatchValidationResult(
        apply_result=PatchApplyResult(
            applied_files=[
                PatchAppliedFile(
                    path="src/app.py",
                    old_content="old\n",
                    new_content="new\n",
                    changed=True,
                )
            ],
            changed_file_count=1,
        ),
        checks=[
            ValidationCheck(
                name="custom",
                command=["custom"],
                result=_command_result(["custom"], return_code=0),
                passed=True,
            )
        ],
        passed=True,
    )


def _command_result(command: list[str], *, return_code: int) -> CommandResult:
    return CommandResult(
        command=command,
        return_code=return_code,
        stdout="stdout",
        stderr="stderr",
        timed_out=False,
    )
