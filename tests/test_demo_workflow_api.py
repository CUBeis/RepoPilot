from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from repopilot.llm import FakeLLMClient
from repopilot.main import app


def test_demo_workflow_api_returns_200() -> None:
    response = TestClient(app).get("/demo/workflow")

    assert response.status_code == 200


def test_demo_workflow_api_returns_successful_final_status() -> None:
    response = TestClient(app).get("/demo/workflow")

    assert response.json()["status"] == "validation_passed"


def test_demo_workflow_api_includes_core_report_fields() -> None:
    response = TestClient(app).get("/demo/workflow")
    data = response.json()

    assert data["issue"] == "Fix login success handling"
    assert data["planned_files"] == ["src/auth.py", "tests/test_auth.py"]
    assert data["proposed_files"] == ["src/auth.py"]
    assert data["changed_files"] == ["src/auth.py"]
    assert data["validation_ran"] is True
    assert data["validation_passed"] is True
    assert "# RepoPilot Workflow Report" in data["markdown_summary"]


def test_demo_workflow_api_does_not_expose_old_or_new_content() -> None:
    response = TestClient(app).get("/demo/workflow")

    assert "old_content" not in response.text
    assert "new_content" not in response.text
    assert "original_content" not in response.text
    assert "proposed_content" not in response.text
    assert "original_preview" not in response.text
    assert "proposed_preview" not in response.text


def test_demo_workflow_api_does_not_expose_stdout_or_stderr_previews() -> None:
    response = TestClient(app).get("/demo/workflow")

    assert "stdout_preview" not in response.text
    assert "stderr_preview" not in response.text
    assert "demo tests passed" not in response.text
    assert "demo lint passed" not in response.text


def test_demo_workflow_api_does_not_execute_workflow_tools(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("demo endpoint must not execute workflow tools")

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

    response = TestClient(app).get("/demo/workflow")

    assert response.status_code == 200


def test_demo_workflow_api_does_not_read_or_write_files(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_file_access(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("demo endpoint must not touch files")

    monkeypatch.setattr(Path, "read_text", fail_file_access)
    monkeypatch.setattr(Path, "read_bytes", fail_file_access)
    monkeypatch.setattr(Path, "write_text", fail_file_access)
    monkeypatch.setattr(Path, "write_bytes", fail_file_access)

    response = TestClient(app).get("/demo/workflow")

    assert response.status_code == 200


def test_demo_workflow_api_is_deterministic() -> None:
    client = TestClient(app)

    first = client.get("/demo/workflow").json()
    second = client.get("/demo/workflow").json()

    assert first == second
