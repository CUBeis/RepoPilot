from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from repopilot.llm import FakeLLMClient, OpenAILLMClient, OpenRouterLLMClient
from repopilot.llm.openrouter_client import OpenRouterLLMError
from repopilot.main import app


def test_agent_preview_returns_200_with_deterministic_planning(
    tmp_path: Path,
) -> None:
    _make_repo(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/agent/preview",
        json={
            "root_path": str(tmp_path),
            "issue": "Fix login validation",
            "use_llm": False,
        },
    )

    assert response.status_code == 200


def test_agent_preview_includes_context_plan_and_patch_preview(
    tmp_path: Path,
) -> None:
    _make_repo(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/agent/preview",
        json={
            "root_path": str(tmp_path),
            "issue": "Fix login validation",
            "use_llm": False,
        },
    )
    body = response.json()

    assert body["issue"] == "Fix login validation"
    assert body["root_name"] == tmp_path.name
    assert body["scanned_file_count"] == 2
    assert body["retrieved_count"] >= 1
    assert body["used_llm"] is False
    assert body["plan"]["objective"] == "Fix login validation"
    assert body["plan"]["relevant_files"] == ["src/auth.py"]
    assert body["patch_proposal"]["target_files"] == ["src/auth.py"]
    assert body["patch_proposal"]["requires_approval"] is True
    assert "# RepoPilot Agent Preview" in body["markdown_summary"]
    assert "Preview only" in body["safety_note"]


def test_agent_preview_uses_openrouter_when_requested(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _make_repo(tmp_path)
    llm_client = FakeOpenRouterClient(make_plan_json())
    monkeypatch.setenv("REPOPILOT_LLM_PROVIDER", "openrouter")
    monkeypatch.setattr(
        OpenRouterLLMClient,
        "from_environment",
        staticmethod(lambda: llm_client),
    )
    client = TestClient(app)

    response = client.post(
        "/agent/preview",
        json={"root_path": str(tmp_path), "issue": "Fix login validation"},
    )
    body = response.json()

    assert response.status_code == 200
    assert body["used_llm"] is True
    assert body["plan"]["confidence"] == 0.8
    assert body["patch_proposal"]["target_files"] == ["src/auth.py"]
    assert llm_client.last_request is not None
    assert llm_client.last_request.model == "openrouter/fake"


def test_agent_preview_uses_openai_when_requested(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _make_repo(tmp_path)
    llm_client = FakeOpenAIClient(make_plan_json())
    monkeypatch.setenv("REPOPILOT_LLM_PROVIDER", "openai")
    monkeypatch.setattr(
        OpenAILLMClient,
        "from_environment",
        staticmethod(lambda: llm_client),
    )
    client = TestClient(app)

    response = client.post(
        "/agent/preview",
        json={"root_path": str(tmp_path), "issue": "Fix login validation"},
    )
    body = response.json()

    assert response.status_code == 200
    assert body["used_llm"] is True
    assert body["plan"]["confidence"] == 0.8
    assert body["patch_proposal"]["target_files"] == ["src/auth.py"]
    assert llm_client.last_request is not None
    assert llm_client.last_request.model == "openai/fake"


def test_agent_preview_missing_openrouter_key_returns_400(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _make_repo(tmp_path)
    monkeypatch.setenv("REPOPILOT_LLM_PROVIDER", "openrouter")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    client = TestClient(app)

    response = client.post(
        "/agent/preview",
        json={"root_path": str(tmp_path), "issue": "Fix login validation"},
    )

    assert response.status_code == 400
    assert "OPENROUTER_API_KEY" in response.json()["detail"]


def test_agent_preview_provider_error_returns_502(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _make_repo(tmp_path)
    monkeypatch.setenv("REPOPILOT_LLM_PROVIDER", "openrouter")
    monkeypatch.setattr(
        OpenRouterLLMClient,
        "from_environment",
        staticmethod(lambda: FailingOpenRouterClient()),
    )
    client = TestClient(app)

    response = client.post(
        "/agent/preview",
        json={"root_path": str(tmp_path), "issue": "Fix login validation"},
    )

    assert response.status_code == 502
    assert "provider unavailable" in response.json()["detail"]


def test_agent_preview_invalid_llm_json_uses_deterministic_fallback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _make_repo(tmp_path)
    llm_client = FakeOpenRouterClient("not json")
    monkeypatch.setenv("REPOPILOT_LLM_PROVIDER", "openrouter")
    monkeypatch.setattr(
        OpenRouterLLMClient,
        "from_environment",
        staticmethod(lambda: llm_client),
    )
    client = TestClient(app)

    response = client.post(
        "/agent/preview",
        json={"root_path": str(tmp_path), "issue": "Fix login validation"},
    )
    body = response.json()

    assert response.status_code == 200
    assert body["used_llm"] is False
    assert body["plan"]["objective"] == "Fix login validation"
    assert "deterministic fallback" in body["markdown_summary"]


def test_agent_preview_returns_null_patch_proposal_when_preview_is_not_safe(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _make_repo(tmp_path)
    llm_client = FakeOpenRouterClient(make_plan_json(relevant_files=["src/missing.py"]))
    monkeypatch.setenv("REPOPILOT_LLM_PROVIDER", "openrouter")
    monkeypatch.setattr(
        OpenRouterLLMClient,
        "from_environment",
        staticmethod(lambda: llm_client),
    )
    client = TestClient(app)

    response = client.post(
        "/agent/preview",
        json={"root_path": str(tmp_path), "issue": "Fix login validation"},
    )

    assert response.status_code == 200
    assert response.json()["patch_proposal"] is None


def test_agent_preview_validates_blank_inputs(tmp_path: Path) -> None:
    _make_repo(tmp_path)
    client = TestClient(app)

    blank_root = client.post(
        "/agent/preview",
        json={
            "root_path": "   ",
            "issue": "Fix login validation",
            "use_llm": False,
        },
    )
    blank_issue = client.post(
        "/agent/preview",
        json={"root_path": str(tmp_path), "issue": "   ", "use_llm": False},
    )

    assert blank_root.status_code == 422
    assert blank_issue.status_code == 422


def test_agent_preview_validates_limits(tmp_path: Path) -> None:
    _make_repo(tmp_path)
    client = TestClient(app)

    invalid_top_k = client.post(
        "/agent/preview",
        json={
            "root_path": str(tmp_path),
            "issue": "Fix login validation",
            "top_k": 0,
            "use_llm": False,
        },
    )
    invalid_preview = client.post(
        "/agent/preview",
        json={
            "root_path": str(tmp_path),
            "issue": "Fix login validation",
            "max_preview_chars": 99,
            "use_llm": False,
        },
    )

    assert invalid_top_k.status_code == 422
    assert invalid_preview.status_code == 422


def test_agent_preview_missing_root_returns_400(tmp_path: Path) -> None:
    client = TestClient(app)

    response = client.post(
        "/agent/preview",
        json={
            "root_path": str(tmp_path / "missing"),
            "issue": "Fix login validation",
            "use_llm": False,
        },
    )

    assert response.status_code == 400
    assert "does not exist" in response.json()["detail"]


def test_agent_preview_bounds_patch_content_and_keeps_paths_relative(
    tmp_path: Path,
) -> None:
    _make_repo(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/agent/preview",
        json={
            "root_path": str(tmp_path),
            "issue": "Fix login validation",
            "max_preview_chars": 100,
            "use_llm": False,
        },
    )
    response_text = response.text
    body = response.json()
    change = body["patch_proposal"]["changes"][0]

    assert len(change["original_preview"]) <= 100
    assert len(change["proposed_preview"]) <= 100
    assert not Path(change["path"]).is_absolute()
    assert str(tmp_path) not in response_text
    assert "TAIL_CONTENT_SHOULD_NOT_LEAK" not in response_text
    assert "old_content" not in response_text
    assert "new_content" not in response_text


def test_agent_preview_does_not_apply_run_repair_or_write_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    files = _make_repo(tmp_path)
    original_content = files[0].read_text(encoding="utf-8")

    def fail_llm_provider(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("LLM provider should not be called in deterministic mode")

    def fail_run_command(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("run_command should not be called")

    def fail_apply_patch(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("apply_patch_proposal should not be called")

    def fail_repair(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("repair generation should not be called")

    def fail_self_correction(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("self-correction should not be started")

    monkeypatch.setattr(
        "repopilot.agent.preview.create_configured_llm_client",
        fail_llm_provider,
    )
    monkeypatch.setattr("repopilot.tools.commands.run_command", fail_run_command)
    monkeypatch.setattr(
        "repopilot.patching.applier.apply_patch_proposal",
        fail_apply_patch,
    )
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
        "/agent/preview",
        json={
            "root_path": str(tmp_path),
            "issue": "Fix login validation",
            "use_llm": False,
        },
    )

    assert response.status_code == 200
    assert files[0].read_text(encoding="utf-8") == original_content


def test_agent_preview_is_deterministic_for_same_repo_and_issue(
    tmp_path: Path,
) -> None:
    _make_repo(tmp_path)
    client = TestClient(app)
    request_body = {
        "root_path": str(tmp_path),
        "issue": "Fix login validation",
        "top_k": 5,
        "max_preview_chars": 120,
        "use_llm": False,
    }

    first = client.post("/agent/preview", json=request_body).json()
    second = client.post("/agent/preview", json=request_body).json()

    assert first == second


def make_plan_json(relevant_files: list[str] | None = None) -> str:
    target_files = relevant_files or ["src/auth.py"]
    return json.dumps(
        {
            "objective": "Fix login validation",
            "relevant_files": target_files,
            "steps": [
                {
                    "order": 1,
                    "description": "Inspect the login validation path.",
                    "target_files": target_files,
                }
            ],
            "risks": ["May affect authentication flow."],
            "assumptions": ["Retrieved chunks are relevant."],
            "confidence": 0.8,
        }
    )


class FakeOpenRouterClient(FakeLLMClient):
    def __init__(self, fixed_response: str) -> None:
        super().__init__(fixed_response)
        self.model = "openrouter/fake"


class FakeOpenAIClient(FakeLLMClient):
    def __init__(self, fixed_response: str) -> None:
        super().__init__(fixed_response)
        self.model = "openai/fake"


class FailingOpenRouterClient:
    model = "openrouter/fake"

    def generate(self, request: object) -> object:
        raise OpenRouterLLMError("provider unavailable")


def _make_repo(root_path: Path) -> list[Path]:
    source_dir = root_path / "src"
    source_dir.mkdir()
    auth_file = source_dir / "auth.py"
    billing_file = source_dir / "billing.py"
    auth_file.write_text(
        "def login_user(credentials):\n"
        "    login_is_valid = bool(credentials)\n"
        "    return login_is_valid\n"
        "# " + ("padding " * 80) + "TAIL_CONTENT_SHOULD_NOT_LEAK\n",
        encoding="utf-8",
    )
    billing_file.write_text(
        "def create_invoice():\n"
        "    return True\n",
        encoding="utf-8",
    )
    (root_path / "image.png").write_bytes(b"not scanned")
    return [auth_file, billing_file]
