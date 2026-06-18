import json
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from repopilot.llm import FakeLLMClient
from repopilot.main import app


def test_repair_approval_api_returns_200_for_valid_request() -> None:
    client = TestClient(app)

    response = client.post("/repairs/approval-request", json=_request_body())

    assert response.status_code == 200


def test_repair_approval_api_response_has_approval_required_true() -> None:
    client = TestClient(app)

    response = client.post("/repairs/approval-request", json=_request_body())

    assert response.json()["approval_required"] is True


def test_repair_approval_api_response_includes_repair_proposal() -> None:
    client = TestClient(app)

    response = client.post("/repairs/approval-request", json=_request_body())
    proposal = response.json()["repair_proposal"]

    assert proposal["summary"] == "Repair login behavior."
    assert proposal["target_files"] == ["src/auth.py"]
    assert proposal["changes"][0]["path"] == "src/auth.py"
    assert proposal["changes"][0]["proposed_content"] == (
        "def login_user():\n    return True\n"
    )


def test_repair_approval_api_forces_repair_proposal_requires_approval() -> None:
    client = TestClient(app)

    response = client.post(
        "/repairs/approval-request",
        json=_request_body(llm_response_json=_repair_json(requires_approval=False)),
    )

    assert response.json()["approval_required"] is True
    assert response.json()["repair_proposal"]["requires_approval"] is True


def test_repair_approval_api_response_includes_failed_attempt_number() -> None:
    client = TestClient(app)

    response = client.post("/repairs/approval-request", json=_request_body())

    assert response.json()["failed_attempt_number"] == 1
    assert "failed attempt 1" in response.json()["summary"]


def test_repair_approval_api_invalid_llm_json_returns_400() -> None:
    client = TestClient(app)

    response = client.post(
        "/repairs/approval-request",
        json=_request_body(llm_response_json="not json"),
    )

    assert response.status_code == 400
    assert "not valid JSON" in response.json()["detail"]


def test_repair_approval_api_invalid_proposal_schema_returns_400() -> None:
    client = TestClient(app)

    response = client.post(
        "/repairs/approval-request",
        json=_request_body(llm_response_json=json.dumps({"summary": "missing"})),
    )

    assert response.status_code == 400
    assert "PatchProposal schema" in response.json()["detail"]


def test_repair_approval_api_passed_attempt_returns_400() -> None:
    client = TestClient(app)

    response = client.post(
        "/repairs/approval-request",
        json=_request_body(failed_attempt=_failed_attempt(passed=True)),
    )

    assert response.status_code == 400
    assert "failed validation attempt" in response.json()["detail"]


def test_repair_approval_api_rejects_file_outside_failed_attempt() -> None:
    client = TestClient(app)

    response = client.post(
        "/repairs/approval-request",
        json=_request_body(
            file_reads=[_file_read("src/auth.py"), _file_read("src/extra.py")],
            llm_response_json=_repair_json(path="src/extra.py"),
        ),
    )

    assert response.status_code == 400
    assert "outside the failed attempt" in response.json()["detail"]


def test_repair_approval_api_rejects_unread_repair_file() -> None:
    client = TestClient(app)

    response = client.post(
        "/repairs/approval-request",
        json=_request_body(
            failed_attempt=_failed_attempt(
                target_files=["src/auth.py", "src/routes.py"],
            ),
            llm_response_json=_repair_json(path="src/routes.py"),
        ),
    )

    assert response.status_code == 400
    assert "not read" in response.json()["detail"]


def test_repair_approval_api_blank_llm_response_returns_validation_error() -> None:
    client = TestClient(app)

    response = client.post(
        "/repairs/approval-request",
        json=_request_body(llm_response_json="   "),
    )

    assert response.status_code == 422


def test_repair_approval_api_invalid_temperature_returns_validation_error() -> None:
    client = TestClient(app)

    response = client.post(
        "/repairs/approval-request",
        json=_request_body(temperature=2.1),
    )

    assert response.status_code == 422


def test_repair_approval_api_invalid_max_tokens_returns_validation_error() -> None:
    client = TestClient(app)

    response = client.post(
        "/repairs/approval-request",
        json=_request_body(max_tokens=0),
    )

    assert response.status_code == 422


def test_repair_approval_api_passes_model_temperature_and_max_tokens(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    instances: list[Any] = []

    class RecordingFakeLLMClient:
        def __init__(self, fixed_response: str) -> None:
            self.inner = FakeLLMClient(fixed_response)
            self.last_request: Any = None
            instances.append(self)

        def generate(self, request: Any) -> Any:
            self.last_request = request
            return self.inner.generate(request)

    monkeypatch.setattr("repopilot.api.repairs.FakeLLMClient", RecordingFakeLLMClient)
    client = TestClient(app)

    response = client.post(
        "/repairs/approval-request",
        json=_request_body(
            model="fake-custom-repairer",
            temperature=0.2,
            max_tokens=700,
        ),
    )

    assert response.status_code == 200
    assert instances[0].last_request.model == "fake-custom-repairer"
    assert instances[0].last_request.temperature == 0.2
    assert instances[0].last_request.max_tokens == 700


def test_repair_approval_api_does_not_apply_run_read_write_or_self_correct(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    marker = tmp_path / "marker.txt"
    marker.write_text("unchanged\n", encoding="utf-8")

    def fail_apply_patch(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("apply_patch_proposal should not be called")

    def fail_run_command(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("run_command should not be called")

    def fail_self_correction(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("self-correction should not be started")

    monkeypatch.setattr(
        "repopilot.patching.applier.apply_patch_proposal",
        fail_apply_patch,
    )
    monkeypatch.setattr("repopilot.tools.commands.run_command", fail_run_command)
    monkeypatch.setattr(
        "repopilot.agent.orchestrator.run_self_correction_loop",
        fail_self_correction,
    )
    client = TestClient(app)

    response = client.post("/repairs/approval-request", json=_request_body())

    assert response.status_code == 200
    assert marker.read_text(encoding="utf-8") == "unchanged\n"


def test_repair_approval_api_uses_fake_llm_not_real_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    used_fake_client = False

    class RecordingFakeLLMClient(FakeLLMClient):
        def generate(self, request: Any) -> Any:
            nonlocal used_fake_client
            used_fake_client = True
            return super().generate(request)

    monkeypatch.setattr("repopilot.api.repairs.FakeLLMClient", RecordingFakeLLMClient)
    client = TestClient(app)

    response = client.post("/repairs/approval-request", json=_request_body())

    assert response.status_code == 200
    assert used_fake_client is True


def test_repair_approval_api_is_deterministic_for_same_payload() -> None:
    client = TestClient(app)
    request_body = _request_body()

    first = client.post("/repairs/approval-request", json=request_body).json()
    second = client.post("/repairs/approval-request", json=request_body).json()

    assert first == second


def _request_body(
    *,
    failed_attempt: dict[str, object] | None = None,
    file_reads: list[dict[str, object]] | None = None,
    llm_response_json: str | None = None,
    model: str = "fake-repair-proposer",
    temperature: float = 0.0,
    max_tokens: int | None = None,
) -> dict[str, object]:
    body: dict[str, object] = {
        "failed_attempt": (
            _failed_attempt() if failed_attempt is None else failed_attempt
        ),
        "file_reads": [_file_read()] if file_reads is None else file_reads,
        "llm_response_json": (
            _repair_json() if llm_response_json is None else llm_response_json
        ),
        "model": model,
        "temperature": temperature,
    }
    if max_tokens is not None:
        body["max_tokens"] = max_tokens
    return body


def _failed_attempt(
    *,
    passed: bool = False,
    target_files: list[str] | None = None,
) -> dict[str, object]:
    targets = ["src/auth.py"] if target_files is None else target_files
    return {
        "attempt_number": 1,
        "proposal": _previous_proposal(targets),
        "validation_result": _validation_result(passed=passed),
        "failure_analysis": _failure_analysis(passed=passed),
    }


def _previous_proposal(target_files: list[str]) -> dict[str, object]:
    change_path = target_files[0] if target_files else "src/auth.py"
    return {
        "summary": "Initial login patch failed.",
        "target_files": target_files,
        "changes": [
            {
                "path": change_path,
                "reason": "Make login return success.",
                "start_line": 1,
                "end_line": 2,
                "original_content": "def login_user():\n    return False\n",
                "proposed_content": "def login_user():\n    return 'yes'\n",
            }
        ],
        "risks": ["May affect authentication flow."],
        "requires_approval": True,
    }


def _validation_result(*, passed: bool) -> dict[str, object]:
    return {
        "apply_result": {
            "applied_files": [
                {
                    "path": "src/auth.py",
                    "old_content": "def login_user():\n    return False\n",
                    "new_content": "def login_user():\n    return 'yes'\n",
                    "changed": True,
                }
            ],
            "changed_file_count": 1,
        },
        "checks": [
            {
                "name": "pytest",
                "command": ["pytest"],
                "result": {
                    "command": ["pytest"],
                    "return_code": 0 if passed else 1,
                    "stdout": "passed" if passed else "login test failed",
                    "stderr": "",
                    "timed_out": False,
                },
                "passed": passed,
            }
        ],
        "passed": passed,
    }


def _failure_analysis(*, passed: bool) -> dict[str, object]:
    if passed:
        return {
            "passed": True,
            "failed_check_count": 0,
            "failed_checks": [],
            "summary": "All validation checks passed.",
            "needs_self_correction": False,
        }

    return {
        "passed": False,
        "failed_check_count": 1,
        "failed_checks": [
            {
                "name": "pytest",
                "command": ["pytest"],
                "return_code": 1,
                "timed_out": False,
                "stdout_excerpt": "pytest failed for login test",
                "stderr_excerpt": "",
            }
        ],
        "summary": "1 validation check failed: pytest failed for login test",
        "needs_self_correction": True,
    }


def _file_read(path: str = "src/auth.py") -> dict[str, object]:
    content = "def login_user():\n    return False\n"
    return {
        "path": path,
        "start_line": 1,
        "end_line": 2,
        "content": content,
        "total_lines": 2,
        "size_bytes": len(content.encode("utf-8")),
    }


def _repair_json(
    *,
    path: str = "src/auth.py",
    requires_approval: bool = True,
) -> str:
    return json.dumps(
        {
            "summary": "Repair login behavior.",
            "target_files": [path],
            "changes": [
                {
                    "path": path,
                    "reason": "Return the expected boolean value.",
                    "start_line": 1,
                    "end_line": 2,
                    "original_content": "def login_user():\n    return False\n",
                    "proposed_content": "def login_user():\n    return True\n",
                }
            ],
            "risks": ["May affect authentication flow."],
            "requires_approval": requires_approval,
        }
    )
