import json

import pytest

from repopilot.chunking.models import CodeChunk
from repopilot.context.models import RepositoryContext
from repopilot.llm import FakeLLMClient
from repopilot.planning import create_llm_implementation_plan
from repopilot.planning.llm_planner import LLMPlanningError
from repopilot.retrieval.models import RetrievedChunk


def make_context() -> RepositoryContext:
    return RepositoryContext(
        root_name="sample",
        scanned_file_count=1,
        total_size_bytes=100,
        skipped_file_count=0,
        total_chunks=1,
        retrieved_chunks=[
            RetrievedChunk(
                chunk=CodeChunk(
                    path="src/auth.py",
                    language="python",
                    chunk_index=0,
                    start_line=1,
                    end_line=3,
                    text="def login_user():\n    pass",
                    sha256="hash",
                ),
                score=3.0,
                matched_terms=["login", "user"],
            )
        ],
    )


def make_plan_json() -> str:
    return json.dumps(
        {
            "objective": "Fix login bug",
            "relevant_files": ["src/auth.py"],
            "steps": [
                {
                    "order": 1,
                    "description": "Inspect the login function.",
                    "target_files": ["src/auth.py"],
                }
            ],
            "risks": ["May affect authentication flow."],
            "assumptions": ["Retrieved chunks are relevant."],
            "confidence": 0.8,
        }
    )


def test_sends_request_through_fake_llm_client() -> None:
    client = FakeLLMClient(make_plan_json())

    create_llm_implementation_plan("Fix login bug", make_context(), client)

    assert client.last_request is not None


def test_sent_request_includes_system_message() -> None:
    client = FakeLLMClient(make_plan_json())

    create_llm_implementation_plan("Fix login bug", make_context(), client)

    assert client.last_request is not None
    assert client.last_request.messages[0].role == "system"
    assert "ImplementationPlan schema" in client.last_request.messages[0].content


def test_sent_request_includes_planning_prompt() -> None:
    client = FakeLLMClient(make_plan_json())

    create_llm_implementation_plan("Fix login bug", make_context(), client)

    assert client.last_request is not None
    user_message = client.last_request.messages[1]
    assert user_message.role == "user"
    assert "Fix login bug" in user_message.content
    assert "src/auth.py" in user_message.content


def test_parses_valid_json_into_implementation_plan() -> None:
    client = FakeLLMClient(make_plan_json())

    plan = create_llm_implementation_plan("Fix login bug", make_context(), client)

    assert plan.objective == "Fix login bug"
    assert plan.relevant_files == ["src/auth.py"]
    assert plan.steps[0].order == 1
    assert plan.confidence == 0.8


def test_parses_json_wrapped_in_markdown_fence() -> None:
    client = FakeLLMClient(f"```json\n{make_plan_json()}\n```")

    plan = create_llm_implementation_plan("Fix login bug", make_context(), client)

    assert plan.objective == "Fix login bug"
    assert plan.relevant_files == ["src/auth.py"]


def test_rejects_invalid_json_with_clear_error() -> None:
    client = FakeLLMClient("not json")

    with pytest.raises(LLMPlanningError, match="not valid JSON"):
        create_llm_implementation_plan("Fix login bug", make_context(), client)


def test_rejects_invalid_plan_structure_with_clear_error() -> None:
    client = FakeLLMClient(json.dumps({"objective": "Missing required fields"}))

    with pytest.raises(LLMPlanningError, match="ImplementationPlan schema"):
        create_llm_implementation_plan("Fix login bug", make_context(), client)


def test_rejects_empty_issue_clearly() -> None:
    client = FakeLLMClient(make_plan_json())

    with pytest.raises(LLMPlanningError, match="issue must not be empty"):
        create_llm_implementation_plan("   ", make_context(), client)


def test_passes_model_temperature_and_max_tokens_into_request() -> None:
    client = FakeLLMClient(make_plan_json())

    create_llm_implementation_plan(
        "Fix login bug",
        make_context(),
        client,
        model="fake-custom",
        temperature=0.2,
        max_tokens=500,
    )

    assert client.last_request is not None
    assert client.last_request.model == "fake-custom"
    assert client.last_request.temperature == 0.2
    assert client.last_request.max_tokens == 500


def test_is_deterministic_with_fake_llm_client() -> None:
    client = FakeLLMClient(make_plan_json())
    context = make_context()

    first_plan = create_llm_implementation_plan("Fix login bug", context, client)
    second_plan = create_llm_implementation_plan("Fix login bug", context, client)

    assert first_plan.model_dump() == second_plan.model_dump()
