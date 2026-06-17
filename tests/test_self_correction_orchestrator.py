from pathlib import Path
from typing import Any

import pytest

from repopilot.agent import run_self_correction_loop
from repopilot.patching import PatchApplyError, PatchProposal, ProposedFileChange
from repopilot.patching.models import PatchAppliedFile, PatchApplyResult
from repopilot.tools.models import CommandResult
from repopilot.validation.models import PatchValidationResult, ValidationCheck


def test_runs_initial_proposal_first(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    initial = _proposal("initial")
    repair = _proposal("repair")
    seen_summaries: list[str] = []

    def fake_apply(*args: Any, **kwargs: Any) -> PatchValidationResult:
        proposal = args[1]
        seen_summaries.append(proposal.summary)
        return _validation_result(passed=True)

    monkeypatch.setattr(
        "repopilot.agent.orchestrator.apply_and_validate_patch",
        fake_apply,
    )

    run_self_correction_loop(
        tmp_path,
        initial,
        approved=True,
        repair_proposals=[repair],
    )

    assert seen_summaries == ["initial"]


def test_stops_when_first_attempt_passes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_apply_results(monkeypatch, [_validation_result(passed=True)])

    result = run_self_correction_loop(
        tmp_path,
        _proposal("initial"),
        approved=True,
        repair_proposals=[_proposal("repair")],
    )

    assert len(result.attempts) == 1
    assert result.final_passed is True
    assert result.stopped_reason == "validation_passed"


def test_analyzes_failures_when_validation_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_apply_results(monkeypatch, [_validation_result(passed=False)])

    result = run_self_correction_loop(tmp_path, _proposal("initial"), approved=True)

    analysis = result.attempts[0].failure_analysis
    assert analysis.failed_check_count == 1
    assert analysis.needs_self_correction is True


def test_retries_with_repair_proposal_when_first_attempt_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    initial = _proposal("initial")
    repair = _proposal("repair")
    _patch_apply_results(
        monkeypatch,
        [_validation_result(passed=False), _validation_result(passed=True)],
    )

    result = run_self_correction_loop(
        tmp_path,
        initial,
        approved=True,
        repair_proposals=[repair],
        max_attempts=2,
    )

    assert [attempt.proposal.summary for attempt in result.attempts] == [
        "initial",
        "repair",
    ]
    assert result.final_passed is True


def test_stops_at_max_attempts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_apply_results(
        monkeypatch,
        [_validation_result(passed=False), _validation_result(passed=False)],
    )

    result = run_self_correction_loop(
        tmp_path,
        _proposal("initial"),
        approved=True,
        repair_proposals=[_proposal("repair 1"), _proposal("repair 2")],
        max_attempts=2,
    )

    assert len(result.attempts) == 2
    assert result.final_passed is False
    assert result.stopped_reason == "max_attempts_reached"


def test_stops_when_no_repair_proposal_is_available(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_apply_results(monkeypatch, [_validation_result(passed=False)])

    result = run_self_correction_loop(
        tmp_path,
        _proposal("initial"),
        approved=True,
        repair_proposals=[],
        max_attempts=3,
    )

    assert len(result.attempts) == 1
    assert result.final_passed is False
    assert result.stopped_reason == "no_repair_proposal_available"


def test_final_passed_reflects_last_successful_validation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_apply_results(
        monkeypatch,
        [_validation_result(passed=False), _validation_result(passed=True)],
    )

    result = run_self_correction_loop(
        tmp_path,
        _proposal("initial"),
        approved=True,
        repair_proposals=[_proposal("repair")],
    )

    assert result.final_passed is True
    assert result.attempts[-1].validation_result.passed is True


def test_stopped_reason_is_clear(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_apply_results(monkeypatch, [_validation_result(passed=False)])

    result = run_self_correction_loop(tmp_path, _proposal("initial"), approved=True)

    assert result.stopped_reason == "no_repair_proposal_available"


def test_propagates_patch_apply_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_apply(*args: Any, **kwargs: Any) -> PatchValidationResult:
        raise PatchApplyError("patch apply failed")

    monkeypatch.setattr(
        "repopilot.agent.orchestrator.apply_and_validate_patch",
        fake_apply,
    )

    with pytest.raises(PatchApplyError, match="patch apply failed"):
        run_self_correction_loop(tmp_path, _proposal("initial"), approved=True)


def test_passes_validation_commands_through(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen_kwargs: list[dict[str, Any]] = []

    def fake_apply(*args: Any, **kwargs: Any) -> PatchValidationResult:
        seen_kwargs.append(kwargs)
        return _validation_result(passed=True)

    monkeypatch.setattr(
        "repopilot.agent.orchestrator.apply_and_validate_patch",
        fake_apply,
    )

    commands = [["pytest", "-q"]]
    run_self_correction_loop(
        tmp_path,
        _proposal("initial"),
        approved=True,
        validation_commands=commands,
        timeout_seconds=12,
    )

    assert seen_kwargs[0]["approved"] is True
    assert seen_kwargs[0]["validation_commands"] == commands
    assert seen_kwargs[0]["timeout_seconds"] == 12


def test_deterministic_structured_result(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_apply_results(monkeypatch, [_validation_result(passed=False)])
    first = run_self_correction_loop(
        tmp_path,
        _proposal("initial"),
        approved=True,
    )

    _patch_apply_results(monkeypatch, [_validation_result(passed=False)])
    second = run_self_correction_loop(
        tmp_path,
        _proposal("initial"),
        approved=True,
    )

    assert first.model_dump() == second.model_dump()


def _patch_apply_results(
    monkeypatch: pytest.MonkeyPatch,
    results: list[PatchValidationResult],
) -> None:
    remaining_results = list(results)

    def fake_apply(*args: Any, **kwargs: Any) -> PatchValidationResult:
        return remaining_results.pop(0)

    monkeypatch.setattr(
        "repopilot.agent.orchestrator.apply_and_validate_patch",
        fake_apply,
    )


def _validation_result(*, passed: bool) -> PatchValidationResult:
    return PatchValidationResult(
        apply_result=PatchApplyResult(
            applied_files=[
                PatchAppliedFile(
                    path="src/auth.py",
                    old_content="old\n",
                    new_content="new\n",
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
                    stdout="passed" if passed else "failed",
                    stderr="",
                    timed_out=False,
                ),
                passed=passed,
            )
        ],
        passed=passed,
    )


def _proposal(summary: str) -> PatchProposal:
    return PatchProposal(
        summary=summary,
        target_files=["src/auth.py"],
        changes=[
            ProposedFileChange(
                path="src/auth.py",
                reason="Apply requested update.",
                start_line=1,
                end_line=1,
                original_content="old\n",
                proposed_content="new\n",
            )
        ],
        risks=[],
        requires_approval=True,
    )
