from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from repopilot.llm import FakeLLMClient
from repopilot.main import app


def test_workflow_report_status_issue_received() -> None:
    response = _post(_request_body())

    assert response.status_code == 200
    assert response.json()["status"] == "issue_received"


def test_workflow_report_status_planned() -> None:
    response = _post(_request_body(plan=_plan()))

    assert response.json()["status"] == "planned"


def test_workflow_report_status_patch_proposed() -> None:
    response = _post(_request_body(patch_proposal=_patch_proposal()))

    assert response.json()["status"] == "patch_proposed"


def test_workflow_report_status_patch_applied() -> None:
    response = _post(_request_body(apply_result=_repair_apply_result()))

    assert response.json()["status"] == "patch_applied"


def test_workflow_report_status_validation_passed() -> None:
    response = _post(_request_body(validation_result=_validation_result(passed=True)))

    assert response.json()["status"] == "validation_passed"


def test_workflow_report_status_validation_failed() -> None:
    response = _post(_request_body(validation_result=_validation_result(passed=False)))

    assert response.json()["status"] == "validation_failed"


def test_workflow_report_status_validation_failed_needs_repair() -> None:
    response = _post(_request_body(failure_analysis=_failure_analysis()))

    assert response.json()["status"] == "validation_failed_needs_repair"


def test_workflow_report_status_repair_waiting_for_approval() -> None:
    response = _post(_request_body(repair_approval=_repair_approval()))

    assert response.json()["status"] == "repair_waiting_for_approval"


def test_workflow_report_status_uses_repair_apply_report_first() -> None:
    response = _post(
        _request_body(
            plan=_plan(),
            patch_proposal=_patch_proposal(),
            validation_result=_validation_result(passed=False),
            failure_analysis=_failure_analysis(),
            repair_approval=_repair_approval(),
            repair_apply_report=_repair_apply_report(
                status="repair_applied_validation_passed"
            ),
        )
    )

    assert response.json()["status"] == "repair_applied_validation_passed"


def test_workflow_report_derives_planned_proposed_and_changed_files() -> None:
    response = _post(
        _request_body(
            plan=_plan(),
            patch_proposal=_patch_proposal(),
            repair_approval=_repair_approval(),
            repair_apply_report=_repair_apply_report(),
        )
    )
    data = response.json()

    assert data["planned_files"] == ["src/app.py", "tests/test_app.py"]
    assert data["proposed_files"] == ["src/app.py", "src/auth.py"]
    assert data["changed_files"] == ["src/auth.py"]


def test_workflow_report_derives_validation_fields_from_validation_result() -> None:
    response = _post(_request_body(validation_result=_validation_result(passed=False)))
    data = response.json()

    assert data["validation_ran"] is True
    assert data["validation_passed"] is False
    assert data["failed_check_count"] == 1


def test_workflow_report_derives_validation_fields_from_repair_apply_report() -> None:
    response = _post(
        _request_body(
            repair_apply_report=_repair_apply_report(
                status="repair_applied_validation_failed"
            )
        )
    )
    data = response.json()

    assert data["validation_ran"] is True
    assert data["validation_passed"] is False
    assert data["failed_check_count"] == 1


def test_workflow_report_derives_repair_and_approval_flags() -> None:
    response = _post(
        _request_body(
            patch_proposal=_patch_proposal(),
            apply_result=_repair_apply_result(),
            repair_approval=_repair_approval(),
        )
    )
    data = response.json()

    assert data["repair_proposed"] is True
    assert data["repair_applied"] is True
    assert data["approval_required"] is True


def test_workflow_report_markdown_summary_is_pr_ready() -> None:
    response = _post(
        _request_body(
            plan=_plan(),
            patch_proposal=_patch_proposal(),
            validation_result=_validation_result(passed=True),
        )
    )
    markdown = response.json()["markdown_summary"]

    assert "# RepoPilot Workflow Report" in markdown
    assert "Fix login bug" in markdown
    assert "src/app.py" in markdown
    assert "Validation passed." in markdown


def test_workflow_report_blank_issue_returns_validation_error() -> None:
    response = _post(_request_body(issue="   "))

    assert response.status_code == 422


def test_workflow_report_response_omits_old_and_new_content() -> None:
    response = _post(
        _request_body(
            patch_proposal=_patch_proposal(),
            repair_approval=_repair_approval(),
        )
    )

    assert "old secret" not in response.text
    assert "new secret" not in response.text
    assert "original_content" not in response.text
    assert "proposed_content" not in response.text
    assert "original_preview" not in response.text
    assert "proposed_preview" not in response.text


def test_workflow_report_response_omits_stdout_and_stderr_previews() -> None:
    response = _post(
        _request_body(
            validation_result=_validation_result(passed=False),
            failure_analysis=_failure_analysis(),
        )
    )

    assert "stdout_preview" not in response.text
    assert "stderr_preview" not in response.text
    assert "stdout_excerpt" not in response.text
    assert "stderr_excerpt" not in response.text
    assert "secret stdout" not in response.text
    assert "secret stderr" not in response.text


def test_workflow_report_api_does_not_execute_workflow_tools(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("workflow report endpoint must not execute tools")

    monkeypatch.setattr("repopilot.repository.scanner.scan_repository", fail)
    monkeypatch.setattr("repopilot.context.builder.build_repository_context", fail)
    monkeypatch.setattr(
        "repopilot.planning.planner.create_implementation_plan",
        fail,
    )
    monkeypatch.setattr("repopilot.patching.applier.apply_patch_proposal", fail)
    monkeypatch.setattr("repopilot.validation.pipeline.apply_and_validate_patch", fail)
    monkeypatch.setattr("repopilot.tools.commands.run_command", fail)
    monkeypatch.setattr(FakeLLMClient, "generate", fail)
    monkeypatch.setattr("repopilot.agent.repair.create_llm_repair_proposal", fail)
    monkeypatch.setattr("repopilot.agent.orchestrator.run_self_correction_loop", fail)
    monkeypatch.setattr(
        "repopilot.validation.failure_analysis.analyze_validation_result",
        fail,
    )

    response = _post(
        _request_body(
            plan=_plan(),
            patch_proposal=_patch_proposal(),
            validation_result=_validation_result(passed=False),
            failure_analysis=_failure_analysis(),
            repair_approval=_repair_approval(),
            repair_apply_report=_repair_apply_report(),
        )
    )

    assert response.status_code == 200


def test_workflow_report_api_does_not_read_or_write_files(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_file_access(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("workflow report endpoint must not touch files")

    monkeypatch.setattr(Path, "read_text", fail_file_access)
    monkeypatch.setattr(Path, "read_bytes", fail_file_access)
    monkeypatch.setattr(Path, "write_text", fail_file_access)
    monkeypatch.setattr(Path, "write_bytes", fail_file_access)

    response = _post(_request_body(plan=_plan()))

    assert response.status_code == 200


def test_workflow_report_api_is_deterministic() -> None:
    body = _request_body(
        plan=_plan(),
        patch_proposal=_patch_proposal(),
        validation_result=_validation_result(passed=False),
        failure_analysis=_failure_analysis(),
        repair_approval=_repair_approval(),
    )

    first = _post(body).json()
    second = _post(body).json()

    assert first == second


def _post(body: dict[str, object]):
    return TestClient(app).post("/reports/workflow", json=body)


def _request_body(
    *,
    issue: str = "Fix login bug",
    plan: dict[str, object] | None = None,
    patch_proposal: dict[str, object] | None = None,
    apply_result: dict[str, object] | None = None,
    validation_result: dict[str, object] | None = None,
    failure_analysis: dict[str, object] | None = None,
    repair_approval: dict[str, object] | None = None,
    repair_apply_report: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "issue": issue,
        "plan": plan,
        "patch_proposal": patch_proposal,
        "apply_result": apply_result,
        "validation_result": validation_result,
        "failure_analysis": failure_analysis,
        "repair_approval": repair_approval,
        "repair_apply_report": repair_apply_report,
    }


def _plan() -> dict[str, object]:
    return {
        "objective": "Fix login bug",
        "relevant_files": ["src/app.py", "tests/test_app.py"],
        "steps": [
            {
                "order": 1,
                "description": "Inspect login behavior.",
                "target_files": ["src/app.py"],
            }
        ],
        "risks": ["May affect login flow."],
        "assumptions": ["Retrieved context is relevant."],
        "confidence": 0.8,
    }


def _patch_proposal() -> dict[str, object]:
    return {
        "summary": "Patch login behavior.",
        "target_files": ["src/app.py"],
        "changes": [
            {
                "path": "src/app.py",
                "reason": "Fix login return value.",
                "start_line": 1,
                "end_line": 2,
                "original_preview": "old secret",
                "proposed_preview": "new secret",
            }
        ],
        "risks": ["May affect login flow."],
        "requires_approval": True,
    }


def _repair_apply_result() -> dict[str, object]:
    return {
        "changed_file_count": 1,
        "applied_files": [
            {"path": "src/app.py", "changed": True},
            {"path": "src/unchanged.py", "changed": False},
        ],
        "validation": None,
    }


def _validation_result(*, passed: bool) -> dict[str, object]:
    return {
        "changed_file_count": 1,
        "applied_files": [{"path": "src/app.py", "changed": True}],
        "checks": [
            _check(
                name="pytest",
                command=["pytest"],
                return_code=0 if passed else 1,
                passed=passed,
            )
        ],
        "passed": passed,
    }


def _failure_analysis() -> dict[str, object]:
    return {
        "passed": False,
        "failed_check_count": 1,
        "failed_checks": [
            {
                "name": "pytest",
                "command": ["pytest"],
                "return_code": 1,
                "timed_out": False,
                "stdout_excerpt": "secret stdout",
                "stderr_excerpt": "secret stderr",
            }
        ],
        "summary": "pytest failed",
        "needs_self_correction": True,
    }


def _repair_approval() -> dict[str, object]:
    return {
        "approval_required": True,
        "summary": "Repair is ready for approval.",
        "failed_attempt_number": 1,
        "repair_proposal": {
            "summary": "Repair login behavior.",
            "target_files": ["src/auth.py", "src/app.py"],
            "changes": [
                {
                    "path": "src/auth.py",
                    "reason": "Fix login return value.",
                    "start_line": 1,
                    "end_line": 2,
                    "original_content": "old secret",
                    "proposed_content": "new secret",
                }
            ],
            "risks": ["May affect auth flow."],
            "requires_approval": True,
        },
    }


def _repair_apply_report(*, status: str = "repair_applied") -> dict[str, object]:
    return {
        "status": status,
        "issue": "Fix login bug",
        "summary": "Repair login behavior.",
        "changed_file_count": 1,
        "changed_files": ["src/auth.py"],
        "validation_ran": status != "repair_applied",
        "validation_passed": (
            None if status == "repair_applied" else status.endswith("_passed")
        ),
        "validation_check_count": 1 if status != "repair_applied" else 0,
        "failed_check_count": (
            1 if status == "repair_applied_validation_failed" else 0
        ),
        "failed_checks": [
            {
                "name": "pytest",
                "command": ["pytest"],
                "return_code": 1,
                "timed_out": False,
            }
        ]
        if status == "repair_applied_validation_failed"
        else [],
        "markdown_summary": "Existing repair report markdown",
    }


def _check(
    *,
    name: str,
    command: list[str],
    return_code: int,
    passed: bool,
) -> dict[str, object]:
    return {
        "name": name,
        "command": command,
        "return_code": return_code,
        "timed_out": False,
        "stdout_preview": "secret stdout",
        "stderr_preview": "secret stderr",
        "passed": passed,
    }
