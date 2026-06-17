import json
from pathlib import Path
from typing import Any

import pytest

from repopilot.agent import (
    LLMRepairProposalError,
    RepairApprovalRequest,
    SelfCorrectionAttempt,
    prepare_repair_for_approval,
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


def test_calls_create_llm_repair_proposal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: dict[str, Any] = {}

    def fake_create(*args: Any, **kwargs: Any) -> PatchProposal:
        seen["args"] = args
        seen["kwargs"] = kwargs
        return _make_repair_proposal()

    monkeypatch.setattr(
        "repopilot.agent.repair_workflow.create_llm_repair_proposal",
        fake_create,
    )
    failed_attempt = _make_failed_attempt()
    file_reads = [_make_file_read()]
    client = FakeLLMClient(_make_repair_json())

    prepare_repair_for_approval(failed_attempt, file_reads, client)

    assert seen["args"] == (failed_attempt, file_reads, client)


def test_returns_repair_approval_request() -> None:
    request = prepare_repair_for_approval(
        _make_failed_attempt(),
        [_make_file_read()],
        FakeLLMClient(_make_repair_json()),
    )

    assert isinstance(request, RepairApprovalRequest)


def test_approval_required_is_true() -> None:
    request = prepare_repair_for_approval(
        _make_failed_attempt(),
        [_make_file_read()],
        FakeLLMClient(_make_repair_json(requires_approval=False)),
    )

    assert request.approval_required is True
    assert request.repair_proposal.requires_approval is True


def test_includes_failed_attempt() -> None:
    failed_attempt = _make_failed_attempt()

    request = prepare_repair_for_approval(
        failed_attempt,
        [_make_file_read()],
        FakeLLMClient(_make_repair_json()),
    )

    assert request.failed_attempt == failed_attempt


def test_includes_repair_proposal() -> None:
    request = prepare_repair_for_approval(
        _make_failed_attempt(),
        [_make_file_read()],
        FakeLLMClient(_make_repair_json()),
    )

    assert request.repair_proposal.summary == "Repair login behavior."
    assert request.repair_proposal.target_files == ["src/auth.py"]


def test_summary_is_clear() -> None:
    request = prepare_repair_for_approval(
        _make_failed_attempt(),
        [_make_file_read()],
        FakeLLMClient(_make_repair_json()),
    )

    assert "Approval required" in request.summary
    assert "failed attempt 1" in request.summary
    assert "Repair login behavior." in request.summary


def test_does_not_apply_patch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_apply_patch(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("apply_patch_proposal should not be called")

    monkeypatch.setattr(
        "repopilot.patching.applier.apply_patch_proposal",
        fail_apply_patch,
    )
    source_file = tmp_path / "src" / "auth.py"
    source_file.parent.mkdir()
    source_file.write_text("def login_user():\n    return False\n", encoding="utf-8")

    prepare_repair_for_approval(
        _make_failed_attempt(),
        [_make_file_read()],
        FakeLLMClient(_make_repair_json()),
    )

    assert source_file.read_text(encoding="utf-8") == (
        "def login_user():\n    return False\n"
    )


def test_does_not_run_validation_commands(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_run_command(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("run_command should not be called")

    monkeypatch.setattr("repopilot.tools.commands.run_command", fail_run_command)

    prepare_repair_for_approval(
        _make_failed_attempt(),
        [_make_file_read()],
        FakeLLMClient(_make_repair_json()),
    )


def test_does_not_call_self_correction_loop(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_loop(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("run_self_correction_loop should not be called")

    monkeypatch.setattr(
        "repopilot.agent.orchestrator.run_self_correction_loop",
        fail_loop,
    )

    prepare_repair_for_approval(
        _make_failed_attempt(),
        [_make_file_read()],
        FakeLLMClient(_make_repair_json()),
    )


def test_propagates_llm_repair_proposal_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_create(*args: Any, **kwargs: Any) -> PatchProposal:
        raise LLMRepairProposalError("repair generation failed")

    monkeypatch.setattr(
        "repopilot.agent.repair_workflow.create_llm_repair_proposal",
        fake_create,
    )

    with pytest.raises(LLMRepairProposalError, match="repair generation failed"):
        prepare_repair_for_approval(
            _make_failed_attempt(),
            [_make_file_read()],
            FakeLLMClient(_make_repair_json()),
        )


def test_passes_model_temperature_and_max_tokens_through(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen_kwargs: dict[str, Any] = {}

    def fake_create(*args: Any, **kwargs: Any) -> PatchProposal:
        seen_kwargs.update(kwargs)
        return _make_repair_proposal()

    monkeypatch.setattr(
        "repopilot.agent.repair_workflow.create_llm_repair_proposal",
        fake_create,
    )

    prepare_repair_for_approval(
        _make_failed_attempt(),
        [_make_file_read()],
        FakeLLMClient(_make_repair_json()),
        model="fake-custom-repairer",
        temperature=0.2,
        max_tokens=700,
    )

    assert seen_kwargs == {
        "model": "fake-custom-repairer",
        "temperature": 0.2,
        "max_tokens": 700,
    }


def test_deterministic_output() -> None:
    failed_attempt = _make_failed_attempt()
    file_reads = [_make_file_read()]
    client = FakeLLMClient(_make_repair_json())

    first = prepare_repair_for_approval(failed_attempt, file_reads, client)
    second = prepare_repair_for_approval(failed_attempt, file_reads, client)

    assert first.model_dump() == second.model_dump()


def _make_failed_attempt() -> SelfCorrectionAttempt:
    return SelfCorrectionAttempt(
        attempt_number=1,
        proposal=PatchProposal(
            summary="Initial login patch failed.",
            target_files=["src/auth.py"],
            changes=[
                ProposedFileChange(
                    path="src/auth.py",
                    reason="Make login return success.",
                    start_line=1,
                    end_line=2,
                    original_content="def login_user():\n    return False\n",
                    proposed_content="def login_user():\n    return 'yes'\n",
                )
            ],
            risks=["May affect authentication flow."],
            requires_approval=True,
        ),
        validation_result=_make_validation_result(),
        failure_analysis=_make_failure_analysis(),
    )


def _make_validation_result() -> PatchValidationResult:
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
                    return_code=1,
                    stdout="login test failed",
                    stderr="",
                    timed_out=False,
                ),
                passed=False,
            )
        ],
        passed=False,
    )


def _make_failure_analysis() -> FailureAnalysis:
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
    content: str = "def login_user():\n    return False\n",
) -> FileReadResult:
    return FileReadResult(
        path="src/auth.py",
        start_line=1,
        end_line=2,
        content=content,
        total_lines=2,
        size_bytes=len(content.encode("utf-8")),
    )


def _make_repair_proposal(
    *,
    requires_approval: bool = True,
) -> PatchProposal:
    return PatchProposal.model_validate(
        json.loads(
            _make_repair_json(
                requires_approval=requires_approval,
            )
        )
    )


def _make_repair_json(
    *,
    requires_approval: bool = True,
) -> str:
    return json.dumps(
        {
            "summary": "Repair login behavior.",
            "target_files": ["src/auth.py"],
            "changes": [
                {
                    "path": "src/auth.py",
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
