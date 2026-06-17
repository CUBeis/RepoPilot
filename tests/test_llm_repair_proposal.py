import json
from pathlib import Path

import pytest

from repopilot.agent import (
    LLMRepairProposalError,
    SelfCorrectionAttempt,
    create_llm_repair_proposal,
)
from repopilot.llm import FakeLLMClient
from repopilot.patching import PatchProposal, ProposedFileChange
from repopilot.patching.models import PatchAppliedFile, PatchApplyResult
from repopilot.tools import FileReadResult
from repopilot.tools.models import CommandResult
from repopilot.validation.models import (
    FailedCheckSummary,
    FailureAnalysis,
    PatchValidationResult,
    ValidationCheck,
)


def test_sends_request_through_fake_llm_client() -> None:
    client = FakeLLMClient(_make_repair_json())

    create_llm_repair_proposal(_make_failed_attempt(), [_make_file_read()], client)

    assert client.last_request is not None


def test_request_includes_system_message() -> None:
    client = FakeLLMClient(_make_repair_json())

    create_llm_repair_proposal(_make_failed_attempt(), [_make_file_read()], client)

    assert client.last_request is not None
    assert client.last_request.messages[0].role == "system"
    assert "repair proposal engine" in client.last_request.messages[0].content


def test_request_includes_failed_attempt_failure_analysis_and_file_contents() -> None:
    client = FakeLLMClient(_make_repair_json())

    create_llm_repair_proposal(_make_failed_attempt(), [_make_file_read()], client)

    assert client.last_request is not None
    user_message = client.last_request.messages[1]
    assert user_message.role == "user"
    assert "Initial login patch failed." in user_message.content
    assert "pytest failed for login test" in user_message.content
    assert "src/auth.py" in user_message.content
    assert "def login_user" in user_message.content


def test_valid_json_becomes_patch_proposal() -> None:
    client = FakeLLMClient(_make_repair_json())

    proposal = create_llm_repair_proposal(
        _make_failed_attempt(),
        [_make_file_read()],
        client,
    )

    assert proposal.summary == "Repair login behavior."
    assert proposal.target_files == ["src/auth.py"]
    assert proposal.changes[0].path == "src/auth.py"
    assert proposal.changes[0].proposed_content == (
        "def login_user():\n    return True\n"
    )


def test_requires_approval_is_forced_true() -> None:
    client = FakeLLMClient(_make_repair_json(requires_approval=False))

    proposal = create_llm_repair_proposal(
        _make_failed_attempt(),
        [_make_file_read()],
        client,
    )

    assert proposal.requires_approval is True


def test_invalid_json_errors_clearly() -> None:
    client = FakeLLMClient("not json")

    with pytest.raises(LLMRepairProposalError, match="not valid JSON"):
        create_llm_repair_proposal(
            _make_failed_attempt(),
            [_make_file_read()],
            client,
        )


def test_invalid_proposal_structure_errors_clearly() -> None:
    client = FakeLLMClient(json.dumps({"summary": "Missing required fields"}))

    with pytest.raises(LLMRepairProposalError, match="PatchProposal schema"):
        create_llm_repair_proposal(
            _make_failed_attempt(),
            [_make_file_read()],
            client,
        )


def test_rejects_passed_attempt() -> None:
    client = FakeLLMClient(_make_repair_json())

    with pytest.raises(LLMRepairProposalError, match="failed validation attempt"):
        create_llm_repair_proposal(
            _make_failed_attempt(passed=True),
            [_make_file_read()],
            client,
        )


def test_rejects_changes_for_files_not_in_failed_attempt() -> None:
    client = FakeLLMClient(_make_repair_json(path="src/extra.py"))

    with pytest.raises(LLMRepairProposalError, match="outside the failed attempt"):
        create_llm_repair_proposal(
            _make_failed_attempt(),
            [_make_file_read("src/auth.py"), _make_file_read("src/extra.py")],
            client,
        )


def test_rejects_changes_for_files_not_read() -> None:
    failed_attempt = _make_failed_attempt(target_files=["src/auth.py", "src/routes.py"])
    client = FakeLLMClient(_make_repair_json(path="src/routes.py"))

    with pytest.raises(LLMRepairProposalError, match="not read"):
        create_llm_repair_proposal(
            failed_attempt,
            [_make_file_read("src/auth.py")],
            client,
        )


def test_allows_extra_file_reads_as_context_without_targeting_them() -> None:
    client = FakeLLMClient(_make_repair_json())

    proposal = create_llm_repair_proposal(
        _make_failed_attempt(),
        [_make_file_read("src/auth.py"), _make_file_read("tests/test_auth.py")],
        client,
    )

    assert proposal.target_files == ["src/auth.py"]


def test_passes_model_temperature_and_max_tokens_into_request() -> None:
    client = FakeLLMClient(_make_repair_json())

    create_llm_repair_proposal(
        _make_failed_attempt(),
        [_make_file_read()],
        client,
        model="fake-custom-repairer",
        temperature=0.2,
        max_tokens=700,
    )

    assert client.last_request is not None
    assert client.last_request.model == "fake-custom-repairer"
    assert client.last_request.temperature == 0.2
    assert client.last_request.max_tokens == 700


def test_is_deterministic_with_fake_llm_client() -> None:
    client = FakeLLMClient(_make_repair_json())
    failed_attempt = _make_failed_attempt()
    file_reads = [_make_file_read()]

    first = create_llm_repair_proposal(failed_attempt, file_reads, client)
    second = create_llm_repair_proposal(failed_attempt, file_reads, client)

    assert first.model_dump() == second.model_dump()


def test_does_not_write_to_disk(tmp_path: Path) -> None:
    source_file = tmp_path / "src" / "auth.py"
    source_file.parent.mkdir()
    source_file.write_text("def login_user():\n    return False\n", encoding="utf-8")
    client = FakeLLMClient(_make_repair_json())

    create_llm_repair_proposal(
        _make_failed_attempt(),
        [_make_file_read()],
        client,
    )

    assert source_file.read_text(encoding="utf-8") == (
        "def login_user():\n    return False\n"
    )


def _make_failed_attempt(
    *,
    passed: bool = False,
    target_files: list[str] | None = None,
) -> SelfCorrectionAttempt:
    proposal = _make_previous_proposal(target_files or ["src/auth.py"])
    return SelfCorrectionAttempt(
        attempt_number=1,
        proposal=proposal,
        validation_result=_make_validation_result(passed=passed),
        failure_analysis=_make_failure_analysis(passed=passed),
    )


def _make_previous_proposal(target_files: list[str]) -> PatchProposal:
    change_path = target_files[0] if target_files else "src/auth.py"
    return PatchProposal(
        summary="Initial login patch failed.",
        target_files=target_files,
        changes=[
            ProposedFileChange(
                path=change_path,
                reason="Make login return success.",
                start_line=1,
                end_line=2,
                original_content="def login_user():\n    return False\n",
                proposed_content="def login_user():\n    return 'yes'\n",
            )
        ],
        risks=["May affect authentication flow."],
        requires_approval=True,
    )


def _make_validation_result(*, passed: bool) -> PatchValidationResult:
    return PatchValidationResult(
        apply_result=PatchApplyResult(
            applied_files=[
                PatchAppliedFile(
                    path="src/auth.py",
                    old_content="def login_user():\n    return False\n",
                    new_content="def login_user():\n    return 'yes'\n",
                    changed=True,
                )
            ],
            changed_file_count=1,
        ),
        checks=[
            ValidationCheck(
                name="pytest",
                command=["pytest"],
                result=CommandResult(
                    command=["pytest"],
                    return_code=0 if passed else 1,
                    stdout="passed" if passed else "login test failed",
                    stderr="",
                    timed_out=False,
                ),
                passed=passed,
            )
        ],
        passed=passed,
    )


def _make_failure_analysis(*, passed: bool) -> FailureAnalysis:
    if passed:
        return FailureAnalysis(
            passed=True,
            failed_check_count=0,
            failed_checks=[],
            summary="All validation checks passed.",
            needs_self_correction=False,
        )

    return FailureAnalysis(
        passed=False,
        failed_check_count=1,
        failed_checks=[
            FailedCheckSummary(
                name="pytest",
                command=["pytest"],
                return_code=1,
                timed_out=False,
                stdout_excerpt="pytest failed for login test",
                stderr_excerpt="",
            )
        ],
        summary="1 validation check failed: pytest failed for login test",
        needs_self_correction=True,
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


def _make_repair_json(
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
