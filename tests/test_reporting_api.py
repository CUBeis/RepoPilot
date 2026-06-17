from typing import Any

import pytest
from fastapi.testclient import TestClient

from repopilot.llm import FakeLLMClient
from repopilot.main import app


def test_report_demo_returns_200() -> None:
    client = TestClient(app)

    response = client.get("/report-demo")

    assert response.status_code == 200


def test_report_demo_json_includes_issue() -> None:
    client = TestClient(app)

    response = client.get("/report-demo")

    assert response.json()["issue"] == "Fix login flow validation"


def test_report_demo_json_includes_status() -> None:
    client = TestClient(app)

    response = client.get("/report-demo")

    assert response.json()["status"] == "validated"


def test_report_demo_json_includes_markdown_summary() -> None:
    client = TestClient(app)

    response = client.get("/report-demo")

    assert "# RepoPilot Run Report" in response.json()["markdown_summary"]


def test_report_demo_markdown_returns_200() -> None:
    client = TestClient(app)

    response = client.get("/report-demo/markdown")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")


def test_report_demo_markdown_contains_heading() -> None:
    client = TestClient(app)

    response = client.get("/report-demo/markdown")

    assert "# RepoPilot Run Report" in response.text


def test_report_demo_endpoints_are_deterministic() -> None:
    client = TestClient(app)

    first_json = client.get("/report-demo").json()
    second_json = client.get("/report-demo").json()
    first_markdown = client.get("/report-demo/markdown").text
    second_markdown = client.get("/report-demo/markdown").text

    assert first_json == second_json
    assert first_markdown == second_markdown


def test_report_demo_endpoints_do_not_call_llms_tools_or_scanner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_generate(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("LLM client should not be called")

    def fail_run_command(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("run_command should not be called")

    def fail_apply_patch(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("apply_patch_proposal should not be called")

    def fail_scan_repository(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("scan_repository should not be called")

    monkeypatch.setattr(FakeLLMClient, "generate", fail_generate)
    monkeypatch.setattr("repopilot.tools.commands.run_command", fail_run_command)
    monkeypatch.setattr(
        "repopilot.patching.applier.apply_patch_proposal",
        fail_apply_patch,
    )
    monkeypatch.setattr(
        "repopilot.repository.scanner.scan_repository",
        fail_scan_repository,
    )
    client = TestClient(app)

    json_response = client.get("/report-demo")
    markdown_response = client.get("/report-demo/markdown")

    assert json_response.status_code == 200
    assert markdown_response.status_code == 200
