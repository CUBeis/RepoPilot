from typing import Any

import pytest
from fastapi.testclient import TestClient

from repopilot.llm import FakeLLMClient
from repopilot.main import app


def test_failure_analysis_api_returns_200_for_passed_validation_result() -> None:
    client = TestClient(app)

    response = client.post(
        "/validation/analyze-failures",
        json={"validation_result": _validation_result(passed=True)},
    )

    assert response.status_code == 200


def test_failure_analysis_api_passed_result_has_no_failed_checks() -> None:
    client = TestClient(app)

    response = client.post(
        "/validation/analyze-failures",
        json={"validation_result": _validation_result(passed=True)},
    )
    body = response.json()

    assert body["passed"] is True
    assert body["failed_check_count"] == 0
    assert body["failed_checks"] == []
    assert body["needs_self_correction"] is False


def test_failure_analysis_api_failed_result_returns_failed_checks() -> None:
    client = TestClient(app)

    response = client.post(
        "/validation/analyze-failures",
        json={
            "validation_result": _validation_result(
                passed=False,
                checks=[
                    _check("pytest", ["pytest"], return_code=1, passed=False),
                    _check(
                        "ruff check .",
                        ["ruff", "check", "."],
                        return_code=0,
                        passed=True,
                    ),
                ],
            )
        },
    )
    failed_check = response.json()["failed_checks"][0]

    assert response.json()["failed_check_count"] == 1
    assert failed_check["name"] == "pytest"
    assert failed_check["command"] == ["pytest"]
    assert failed_check["return_code"] == 1
    assert "pytest exited with return code 1" in response.json()["summary"]


def test_failure_analysis_api_represents_timeout_failure() -> None:
    client = TestClient(app)

    response = client.post(
        "/validation/analyze-failures",
        json={
            "validation_result": _validation_result(
                passed=False,
                checks=[
                    _check(
                        "pytest",
                        ["pytest"],
                        return_code=-1,
                        passed=False,
                        timed_out=True,
                    )
                ],
            )
        },
    )

    assert response.json()["failed_checks"][0]["timed_out"] is True
    assert "pytest timed out" in response.json()["summary"]


def test_failure_analysis_api_stdout_and_stderr_excerpts_are_bounded() -> None:
    client = TestClient(app)

    response = client.post(
        "/validation/analyze-failures",
        json={
            "validation_result": _validation_result(
                passed=False,
                checks=[
                    _check(
                        "pytest",
                        ["pytest"],
                        return_code=1,
                        passed=False,
                        stdout="a" * 2000,
                        stderr="b" * 2000,
                    )
                ],
            )
        },
    )
    failed_check = response.json()["failed_checks"][0]

    assert len(failed_check["stdout_excerpt"]) == 1000
    assert len(failed_check["stderr_excerpt"]) == 1000


def test_failure_analysis_api_max_excerpt_chars_controls_truncation() -> None:
    client = TestClient(app)

    response = client.post(
        "/validation/analyze-failures",
        json={
            "validation_result": _validation_result(
                passed=False,
                checks=[
                    _check(
                        "pytest",
                        ["pytest"],
                        return_code=1,
                        passed=False,
                        stdout="abcdef",
                        stderr="uvwxyz",
                    )
                ],
            ),
            "max_excerpt_chars": 3,
        },
    )
    failed_check = response.json()["failed_checks"][0]

    assert failed_check["stdout_excerpt"] == "abc"
    assert failed_check["stderr_excerpt"] == "uvw"


def test_failure_analysis_api_invalid_max_excerpt_chars_returns_error() -> None:
    client = TestClient(app)

    response = client.post(
        "/validation/analyze-failures",
        json={
            "validation_result": _validation_result(passed=False),
            "max_excerpt_chars": 5001,
        },
    )

    assert response.status_code == 422


def test_failure_analysis_api_response_omits_old_and_new_content() -> None:
    client = TestClient(app)

    response = client.post(
        "/validation/analyze-failures",
        json={"validation_result": _validation_result(passed=False)},
    )

    assert "old_content" not in response.text
    assert "new_content" not in response.text


def test_failure_analysis_api_does_not_run_commands_apply_patches_or_mutate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_run_command(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("run_command should not be called")

    def fail_apply_patch(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("apply_patch_proposal should not be called")

    monkeypatch.setattr("repopilot.tools.commands.run_command", fail_run_command)
    monkeypatch.setattr(
        "repopilot.patching.applier.apply_patch_proposal",
        fail_apply_patch,
    )
    client = TestClient(app)

    response = client.post(
        "/validation/analyze-failures",
        json={"validation_result": _validation_result(passed=False)},
    )

    assert response.status_code == 200


def test_failure_analysis_api_does_not_call_llms_generate_repairs_or_self_correct(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_generate(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("LLM client should not be called")

    def fail_repair(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("repair generation should not be called")

    def fail_self_correction(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("self-correction should not be started")

    monkeypatch.setattr(FakeLLMClient, "generate", fail_generate)
    monkeypatch.setattr(
        "repopilot.agent.repair.create_llm_repair_proposal",
        fail_repair,
    )
    monkeypatch.setattr(
        "repopilot.agent.orchestrator.run_self_correction_loop",
        fail_self_correction,
    )
    client = TestClient(app)

    response = client.post(
        "/validation/analyze-failures",
        json={"validation_result": _validation_result(passed=False)},
    )

    assert response.status_code == 200


def test_failure_analysis_api_is_deterministic_for_same_payload() -> None:
    client = TestClient(app)
    request_body = {"validation_result": _validation_result(passed=False)}

    first = client.post("/validation/analyze-failures", json=request_body).json()
    second = client.post("/validation/analyze-failures", json=request_body).json()

    assert first == second


def _validation_result(
    *,
    passed: bool,
    checks: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    return {
        "apply_result": {
            "applied_files": [
                {
                    "path": "src/app.py",
                    "old_content": "old\n",
                    "new_content": "new\n",
                    "changed": True,
                }
            ],
            "changed_file_count": 1,
        },
        "checks": (
            [_check("pytest", ["pytest"], return_code=0, passed=True)]
            if checks is None
            else checks
        ),
        "passed": passed,
    }


def _check(
    name: str,
    command: list[str],
    *,
    return_code: int,
    passed: bool,
    stdout: str = "stdout",
    stderr: str = "stderr",
    timed_out: bool = False,
) -> dict[str, object]:
    return {
        "name": name,
        "command": command,
        "result": {
            "command": command,
            "return_code": return_code,
            "stdout": stdout,
            "stderr": stderr,
            "timed_out": timed_out,
        },
        "passed": passed,
    }
