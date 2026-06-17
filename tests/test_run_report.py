from pathlib import Path
from typing import Any

import pytest

from repopilot.agent import (
    RepairApprovalRequest,
    SelfCorrectionAttempt,
    SelfCorrectionResult,
)
from repopilot.llm import FakeLLMClient
from repopilot.patching import PatchProposal, ProposedFileChange
from repopilot.patching.models import PatchAppliedFile, PatchApplyResult
from repopilot.planning import ImplementationPlan, PlanStep
from repopilot.reporting import AgentRunReport, create_agent_run_report
from repopilot.tools.models import CommandResult
from repopilot.validation.models import (
    FailedCheckSummary,
    FailureAnalysis,
    PatchValidationResult,
    ValidationCheck,
)


def test_creates_report_from_issue_only() -> None:
    report = create_agent_run_report(issue="Fix login bug")

    assert report.issue == "Fix login bug"
    assert report.status == "issue_received"
    assert report.summary == "Issue received: Fix login bug"
    assert report.validation_passed is None


def test_includes_planned_files_from_plan() -> None:
    report = create_agent_run_report(issue="Fix login bug", plan=_make_plan())

    assert report.status == "planned"
    assert report.planned_files == ["src/auth.py", "tests/test_auth.py"]


def test_includes_proposed_files_from_patch_proposal() -> None:
    report = create_agent_run_report(
        issue="Fix login bug",
        patch_proposal=_make_patch_proposal(),
    )

    assert report.status == "proposal_ready"
    assert report.proposed_files == ["src/auth.py"]


def test_marks_approval_required_when_proposal_requires_approval() -> None:
    report = create_agent_run_report(
        issue="Fix login bug",
        patch_proposal=_make_patch_proposal(requires_approval=True),
    )

    assert report.approval_required is True


def test_includes_changed_files_from_validation_result() -> None:
    report = create_agent_run_report(
        issue="Fix login bug",
        validation_result=_make_validation_result(passed=True),
    )

    assert report.changed_files == ["src/auth.py"]


def test_marks_validation_passed_true_when_validation_passed() -> None:
    report = create_agent_run_report(
        issue="Fix login bug",
        validation_result=_make_validation_result(passed=True),
    )

    assert report.status == "validated"
    assert report.validation_passed is True


def test_marks_validation_failed_when_validation_failed() -> None:
    report = create_agent_run_report(
        issue="Fix login bug",
        validation_result=_make_validation_result(passed=False),
    )

    assert report.status == "validation_failed"
    assert report.validation_passed is False


def test_includes_failed_check_names_from_failure_analysis() -> None:
    report = create_agent_run_report(
        issue="Fix login bug",
        validation_result=_make_validation_result(passed=False),
        failure_analysis=_make_failure_analysis(),
    )

    assert report.failed_checks == ["pytest", "ruff"]
    assert report.summary == "2 validation checks failed."


def test_marks_repair_ready_for_approval_when_repair_request_exists() -> None:
    repair_request = _make_repair_approval_request()

    report = create_agent_run_report(
        issue="Fix login bug",
        repair_approval_request=repair_request,
    )

    assert report.status == "repair_ready_for_approval"
    assert report.repair_proposed is True
    assert report.approval_required is True
    assert report.summary == repair_request.summary


def test_includes_self_correction_stopped_reason() -> None:
    report = create_agent_run_report(
        issue="Fix login bug",
        self_correction_result=_make_self_correction_result(final_passed=False),
    )

    assert report.stopped_reason == "max_attempts_reached"


def test_marks_self_correction_complete_when_final_passed_true() -> None:
    report = create_agent_run_report(
        issue="Fix login bug",
        self_correction_result=_make_self_correction_result(final_passed=True),
    )

    assert report.status == "self_correction_complete"


def test_marks_self_correction_failed_when_final_passed_false() -> None:
    report = create_agent_run_report(
        issue="Fix login bug",
        self_correction_result=_make_self_correction_result(final_passed=False),
    )

    assert report.status == "self_correction_failed"


def test_creates_readable_markdown_summary() -> None:
    report = create_agent_run_report(
        issue="Fix login bug",
        plan=_make_plan(),
        patch_proposal=_make_patch_proposal(),
        validation_result=_make_validation_result(passed=False),
        failure_analysis=_make_failure_analysis(),
    )

    assert "# RepoPilot Run Report" in report.markdown_summary
    assert "**Issue:** Fix login bug" in report.markdown_summary
    assert "**Status:** validation_failed" in report.markdown_summary
    assert "- Failed checks: pytest, ruff" in report.markdown_summary


def test_deterministic_output() -> None:
    kwargs = {
        "issue": "Fix login bug",
        "plan": _make_plan(),
        "patch_proposal": _make_patch_proposal(),
        "validation_result": _make_validation_result(passed=False),
        "failure_analysis": _make_failure_analysis(),
    }

    first = create_agent_run_report(**kwargs)
    second = create_agent_run_report(**kwargs)

    assert first.model_dump() == second.model_dump()


def test_returns_agent_run_report_model() -> None:
    report = create_agent_run_report(issue="Fix login bug")

    assert isinstance(report, AgentRunReport)


def test_does_not_call_llms_run_commands_or_write_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_file = tmp_path / "auth.py"
    source_file.write_text("original", encoding="utf-8")

    def fail_generate(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("LLM client should not be called")

    def fail_run_command(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("run_command should not be called")

    def fail_apply_patch(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("apply_patch_proposal should not be called")

    monkeypatch.setattr(FakeLLMClient, "generate", fail_generate)
    monkeypatch.setattr("repopilot.tools.commands.run_command", fail_run_command)
    monkeypatch.setattr(
        "repopilot.patching.applier.apply_patch_proposal",
        fail_apply_patch,
    )

    create_agent_run_report(
        issue="Fix login bug",
        plan=_make_plan(),
        patch_proposal=_make_patch_proposal(),
    )

    assert source_file.read_text(encoding="utf-8") == "original"


def _make_plan() -> ImplementationPlan:
    return ImplementationPlan(
        objective="Fix login bug",
        relevant_files=["src/auth.py", "tests/test_auth.py", "src/auth.py"],
        steps=[
            PlanStep(
                order=1,
                description="Inspect login behavior.",
                target_files=["src/auth.py"],
            )
        ],
        risks=["May affect authentication flow."],
        assumptions=["Retrieved files are relevant."],
        confidence=0.8,
    )


def _make_patch_proposal(*, requires_approval: bool = True) -> PatchProposal:
    return PatchProposal(
        summary="Update login behavior.",
        target_files=["src/auth.py"],
        changes=[
            ProposedFileChange(
                path="src/auth.py",
                reason="Return the expected boolean value.",
                start_line=1,
                end_line=2,
                original_content="def login_user():\n    return False\n",
                proposed_content="def login_user():\n    return True\n",
            )
        ],
        risks=["May affect authentication flow."],
        requires_approval=requires_approval,
    )


def _make_validation_result(*, passed: bool) -> PatchValidationResult:
    return PatchValidationResult(
        apply_result=PatchApplyResult(
            applied_files=[
                PatchAppliedFile(
                    path="src/auth.py",
                    old_content="def login_user():\n    return False\n",
                    new_content="def login_user():\n    return True\n",
                    changed=True,
                ),
                PatchAppliedFile(
                    path="README.md",
                    old_content="docs",
                    new_content="docs",
                    changed=False,
                ),
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
                    stdout="passed" if passed else "failed",
                    stderr="",
                    timed_out=False,
                ),
                passed=passed,
            )
        ],
        passed=passed,
    )


def _make_failure_analysis() -> FailureAnalysis:
    return FailureAnalysis(
        passed=False,
        failed_check_count=2,
        failed_checks=[
            FailedCheckSummary(
                name="pytest",
                command=["pytest"],
                return_code=1,
                timed_out=False,
                stdout_excerpt="test failed",
                stderr_excerpt="",
            ),
            FailedCheckSummary(
                name="ruff",
                command=["ruff", "check", "."],
                return_code=1,
                timed_out=False,
                stdout_excerpt="lint failed",
                stderr_excerpt="",
            ),
        ],
        summary="2 validation checks failed.",
        needs_self_correction=True,
    )


def _make_failed_attempt() -> SelfCorrectionAttempt:
    validation_result = _make_validation_result(passed=False)
    return SelfCorrectionAttempt(
        attempt_number=1,
        proposal=_make_patch_proposal(),
        validation_result=validation_result,
        failure_analysis=_make_failure_analysis(),
    )


def _make_repair_approval_request() -> RepairApprovalRequest:
    return RepairApprovalRequest(
        failed_attempt=_make_failed_attempt(),
        repair_proposal=_make_patch_proposal(),
        approval_required=True,
        summary="Approval required for repair proposal.",
    )


def _make_self_correction_result(*, final_passed: bool) -> SelfCorrectionResult:
    return SelfCorrectionResult(
        attempts=[_make_failed_attempt()],
        final_passed=final_passed,
        stopped_reason=(
            "validation_passed" if final_passed else "max_attempts_reached"
        ),
    )
