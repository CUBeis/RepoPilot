from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from repopilot.llm import FakeLLMClient
from repopilot.main import app


def test_repair_apply_report_api_returns_200_without_validation() -> None:
    client = TestClient(app)

    response = client.post(
        "/reports/repair-apply-result",
        json=_request_body(),
    )

    assert response.status_code == 200


def test_repair_apply_report_status_is_repair_applied_without_validation() -> None:
    client = TestClient(app)

    response = client.post(
        "/reports/repair-apply-result",
        json=_request_body(),
    )

    assert response.json()["status"] == "repair_applied"


def test_repair_apply_report_validation_flags_without_validation() -> None:
    client = TestClient(app)

    response = client.post(
        "/reports/repair-apply-result",
        json=_request_body(),
    )

    assert response.json()["validation_ran"] is False
    assert response.json()["validation_passed"] is None


def test_repair_apply_report_changed_files_come_from_applied_files() -> None:
    client = TestClient(app)

    response = client.post(
        "/reports/repair-apply-result",
        json=_request_body(),
    )

    assert response.json()["changed_files"] == ["src/app.py"]


def test_repair_apply_report_markdown_includes_key_summary_fields() -> None:
    client = TestClient(app)

    response = client.post(
        "/reports/repair-apply-result",
        json=_request_body(),
    )
    markdown = response.json()["markdown_summary"]

    assert "# RepoPilot Repair Apply Report" in markdown
    assert "Fix login bug" in markdown
    assert "Repair login behavior" in markdown
    assert "src/app.py" in markdown


def test_repair_apply_report_status_when_validation_passed() -> None:
    client = TestClient(app)

    response = client.post(
        "/reports/repair-apply-result",
        json=_request_body(validation=_validation(passed=True)),
    )

    assert response.json()["status"] == "repair_applied_validation_passed"
    assert response.json()["validation_ran"] is True
    assert response.json()["validation_passed"] is True


def test_repair_apply_report_status_when_validation_failed() -> None:
    client = TestClient(app)

    response = client.post(
        "/reports/repair-apply-result",
        json=_request_body(validation=_validation(passed=False)),
    )

    assert response.json()["status"] == "repair_applied_validation_failed"
    assert response.json()["validation_ran"] is True
    assert response.json()["validation_passed"] is False


def test_repair_apply_report_failed_check_count_counts_only_failed_checks() -> None:
    client = TestClient(app)

    response = client.post(
        "/reports/repair-apply-result",
        json=_request_body(validation=_validation_with_mixed_checks()),
    )

    assert response.json()["validation_check_count"] == 2
    assert response.json()["failed_check_count"] == 1


def test_repair_apply_report_failed_checks_include_safe_metadata() -> None:
    client = TestClient(app)

    response = client.post(
        "/reports/repair-apply-result",
        json=_request_body(validation=_validation_with_mixed_checks()),
    )

    assert response.json()["failed_checks"] == [
        {
            "name": "pytest",
            "command": ["pytest"],
            "return_code": 1,
            "timed_out": False,
        }
    ]


def test_repair_apply_report_blank_issue_returns_validation_error() -> None:
    client = TestClient(app)

    response = client.post(
        "/reports/repair-apply-result",
        json=_request_body(issue="   "),
    )

    assert response.status_code == 422


def test_repair_apply_report_blank_summary_returns_validation_error() -> None:
    client = TestClient(app)

    response = client.post(
        "/reports/repair-apply-result",
        json=_request_body(repair_summary="   "),
    )

    assert response.status_code == 422


def test_repair_apply_report_response_omits_old_and_new_content() -> None:
    client = TestClient(app)
    body = _request_body()
    body["repair_result"]["applied_files"][0]["old_content"] = "old"
    body["repair_result"]["applied_files"][0]["new_content"] = "new"

    response = client.post("/reports/repair-apply-result", json=body)

    assert "old_content" not in response.text
    assert "new_content" not in response.text


def test_repair_apply_report_response_omits_validation_output_previews() -> None:
    client = TestClient(app)

    response = client.post(
        "/reports/repair-apply-result",
        json=_request_body(validation=_validation(passed=False)),
    )

    assert "stdout_preview" not in response.text
    assert "stderr_preview" not in response.text
    assert "hidden stdout" not in response.text
    assert "hidden stderr" not in response.text


def test_repair_apply_report_api_does_not_apply_patches_or_run_commands(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_apply(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("patch application should not run")

    def fail_validate(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("validation pipeline should not run")

    def fail_run_command(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("commands should not run")

    monkeypatch.setattr("repopilot.patching.applier.apply_patch_proposal", fail_apply)
    monkeypatch.setattr(
        "repopilot.validation.pipeline.apply_and_validate_patch",
        fail_validate,
    )
    monkeypatch.setattr("repopilot.tools.commands.run_command", fail_run_command)
    client = TestClient(app)

    response = client.post(
        "/reports/repair-apply-result",
        json=_request_body(validation=_validation(passed=True)),
    )

    assert response.status_code == 200


def test_repair_apply_report_api_does_not_call_llms_or_generate_repairs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_generate(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("LLM client should not be called")

    def fail_repair_generation(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("repair generation should not run")

    def fail_repair_workflow(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("repair approval workflow should not run")

    def fail_self_correction(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("self-correction should not start")

    def fail_failure_analysis(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("failure analysis should not run")

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
        "/reports/repair-apply-result",
        json=_request_body(validation=_validation(passed=False)),
    )

    assert response.status_code == 200


def test_repair_apply_report_api_does_not_read_or_write_files(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_file_access(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("filesystem access should not happen")

    monkeypatch.setattr(Path, "read_text", fail_file_access)
    monkeypatch.setattr(Path, "read_bytes", fail_file_access)
    monkeypatch.setattr(Path, "write_text", fail_file_access)
    monkeypatch.setattr(Path, "write_bytes", fail_file_access)
    client = TestClient(app)

    response = client.post(
        "/reports/repair-apply-result",
        json=_request_body(),
    )

    assert response.status_code == 200


def test_repair_apply_report_api_is_deterministic() -> None:
    client = TestClient(app)
    body = _request_body(validation=_validation_with_mixed_checks())

    first = client.post("/reports/repair-apply-result", json=body).json()
    second = client.post("/reports/repair-apply-result", json=body).json()

    assert first == second


def _request_body(
    *,
    issue: str = "Fix login bug",
    repair_summary: str = "Repair login behavior",
    validation: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "issue": issue,
        "repair_summary": repair_summary,
        "repair_result": _repair_result(validation=validation),
    }


def _repair_result(
    *,
    validation: dict[str, object] | None,
) -> dict[str, object]:
    return {
        "changed_file_count": 1,
        "applied_files": [
            {"path": "src/app.py", "changed": True},
            {"path": "src/unchanged.py", "changed": False},
        ],
        "validation": validation,
    }


def _validation(*, passed: bool) -> dict[str, object]:
    return {
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


def _validation_with_mixed_checks() -> dict[str, object]:
    return {
        "checks": [
            _check(
                name="pytest",
                command=["pytest"],
                return_code=1,
                passed=False,
            ),
            _check(
                name="ruff check .",
                command=["ruff", "check", "."],
                return_code=0,
                passed=True,
            ),
        ],
        "passed": False,
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
        "stdout_preview": "hidden stdout",
        "stderr_preview": "hidden stderr",
        "passed": passed,
    }
