import json
from pathlib import Path

import pytest

from repopilot.llm import FakeLLMClient
from repopilot.patching import (
    LLMPatchProposalError,
    create_llm_patch_proposal,
)
from repopilot.planning import ImplementationPlan, PlanStep
from repopilot.tools import FileReadResult, read_text_file


def test_sends_request_through_fake_llm_client() -> None:
    client = FakeLLMClient(_make_proposal_json())

    create_llm_patch_proposal(_make_plan(), [_make_file_read()], client)

    assert client.last_request is not None


def test_request_includes_system_message() -> None:
    client = FakeLLMClient(_make_proposal_json())

    create_llm_patch_proposal(_make_plan(), [_make_file_read()], client)

    assert client.last_request is not None
    assert client.last_request.messages[0].role == "system"
    assert "PatchProposal schema" in client.last_request.messages[0].content


def test_request_includes_plan_details_and_file_contents() -> None:
    client = FakeLLMClient(_make_proposal_json())

    create_llm_patch_proposal(_make_plan(), [_make_file_read()], client)

    assert client.last_request is not None
    user_message = client.last_request.messages[1]
    assert user_message.role == "user"
    assert "Fix login behavior" in user_message.content
    assert "Inspect the login implementation." in user_message.content
    assert "src/auth.py" in user_message.content
    assert "def login_user" in user_message.content


def test_valid_json_becomes_patch_proposal() -> None:
    client = FakeLLMClient(_make_proposal_json())

    proposal = create_llm_patch_proposal(_make_plan(), [_make_file_read()], client)

    assert proposal.summary == "Update login behavior."
    assert proposal.target_files == ["src/auth.py"]
    assert proposal.changes[0].path == "src/auth.py"
    assert proposal.changes[0].proposed_content == (
        "def login_user():\n    return True\n"
    )


def test_requires_approval_is_forced_true() -> None:
    client = FakeLLMClient(_make_proposal_json(requires_approval=False))

    proposal = create_llm_patch_proposal(_make_plan(), [_make_file_read()], client)

    assert proposal.requires_approval is True


def test_invalid_json_errors_clearly() -> None:
    client = FakeLLMClient("not json")

    with pytest.raises(LLMPatchProposalError, match="not valid JSON"):
        create_llm_patch_proposal(_make_plan(), [_make_file_read()], client)


def test_invalid_proposal_structure_errors_clearly() -> None:
    client = FakeLLMClient(json.dumps({"summary": "Missing required fields"}))

    with pytest.raises(LLMPatchProposalError, match="PatchProposal schema"):
        create_llm_patch_proposal(_make_plan(), [_make_file_read()], client)


def test_rejects_changes_for_files_not_in_plan() -> None:
    client = FakeLLMClient(_make_proposal_json(path="src/extra.py"))

    with pytest.raises(LLMPatchProposalError, match="outside the implementation plan"):
        create_llm_patch_proposal(_make_plan(), [_make_file_read()], client)


def test_rejects_changes_for_files_not_read() -> None:
    plan = _make_plan(["src/auth.py", "src/routes.py"])
    client = FakeLLMClient(_make_proposal_json(path="src/routes.py"))

    with pytest.raises(LLMPatchProposalError, match="not read"):
        create_llm_patch_proposal(plan, [_make_file_read("src/auth.py")], client)


def test_passes_model_temperature_and_max_tokens_into_request() -> None:
    client = FakeLLMClient(_make_proposal_json())

    create_llm_patch_proposal(
        _make_plan(),
        [_make_file_read()],
        client,
        model="fake-custom-patcher",
        temperature=0.2,
        max_tokens=600,
    )

    assert client.last_request is not None
    assert client.last_request.model == "fake-custom-patcher"
    assert client.last_request.temperature == 0.2
    assert client.last_request.max_tokens == 600


def test_is_deterministic_with_fake_llm_client() -> None:
    client = FakeLLMClient(_make_proposal_json())
    plan = _make_plan()
    file_reads = [_make_file_read()]

    first = create_llm_patch_proposal(plan, file_reads, client)
    second = create_llm_patch_proposal(plan, file_reads, client)

    assert first.model_dump() == second.model_dump()


def test_does_not_write_to_disk(tmp_path: Path) -> None:
    source_file = tmp_path / "src" / "auth.py"
    source_file.parent.mkdir()
    source_file.write_text("def login_user():\n    return False\n", encoding="utf-8")

    file_read = read_text_file(tmp_path, "src/auth.py")
    client = FakeLLMClient(_make_proposal_json())

    create_llm_patch_proposal(_make_plan(), [file_read], client)

    assert source_file.read_text(encoding="utf-8") == (
        "def login_user():\n    return False\n"
    )


def _make_plan(relevant_files: list[str] | None = None) -> ImplementationPlan:
    files = relevant_files or ["src/auth.py"]
    return ImplementationPlan(
        objective="Fix login behavior",
        relevant_files=files,
        steps=[
            PlanStep(
                order=1,
                description="Inspect the login implementation.",
                target_files=["src/auth.py"],
            )
        ],
        risks=["May affect authentication flow."],
        assumptions=["Read-only context is enough."],
        confidence=0.8,
    )


def _make_file_read(
    path: str = "src/auth.py",
    content: str = "def login_user():\n    return False\n",
) -> FileReadResult:
    return FileReadResult(
        path=path,
        start_line=1,
        end_line=2,
        content=content,
        total_lines=2,
        size_bytes=len(content.encode("utf-8")),
    )


def _make_proposal_json(
    *,
    path: str = "src/auth.py",
    requires_approval: bool = True,
) -> str:
    return json.dumps(
        {
            "summary": "Update login behavior.",
            "target_files": [path],
            "changes": [
                {
                    "path": path,
                    "reason": "Make login return success.",
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
