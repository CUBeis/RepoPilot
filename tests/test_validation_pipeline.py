from pathlib import Path
from typing import Any

import pytest

from repopilot.patching import PatchApplyError, PatchProposal, ProposedFileChange
from repopilot.patching.models import PatchAppliedFile, PatchApplyResult
from repopilot.tools.models import CommandResult
from repopilot.validation import apply_and_validate_patch


def test_applies_patch_then_runs_validation_commands(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []

    def fake_apply(*args: Any, **kwargs: Any) -> PatchApplyResult:
        events.append("apply")
        return _apply_result()

    def fake_run_command(*args: Any, **kwargs: Any) -> CommandResult:
        events.append("run")
        return _command_result(args[1], return_code=0)

    monkeypatch.setattr(
        "repopilot.validation.pipeline.apply_patch_proposal",
        fake_apply,
    )
    monkeypatch.setattr("repopilot.validation.pipeline.run_command", fake_run_command)

    apply_and_validate_patch(
        tmp_path,
        _proposal(),
        approved=True,
        validation_commands=[["pytest"]],
    )

    assert events == ["apply", "run"]


def test_returns_passed_true_when_all_checks_pass(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_apply(monkeypatch)
    _patch_run_command(
        monkeypatch,
        [
            _command_result(["pytest"], return_code=0),
            _command_result(["ruff", "check", "."], return_code=0),
        ],
    )

    result = apply_and_validate_patch(
        tmp_path,
        _proposal(),
        approved=True,
        validation_commands=[["pytest"], ["ruff", "check", "."]],
    )

    assert result.passed is True
    assert [check.passed for check in result.checks] == [True, True]


def test_returns_passed_false_when_command_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_apply(monkeypatch)
    _patch_run_command(monkeypatch, [_command_result(["pytest"], return_code=1)])

    result = apply_and_validate_patch(
        tmp_path,
        _proposal(),
        approved=True,
        validation_commands=[["pytest"]],
    )

    assert result.passed is False
    assert result.checks[0].passed is False


def test_returns_passed_false_when_command_times_out(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_apply(monkeypatch)
    _patch_run_command(
        monkeypatch,
        [_command_result(["pytest"], return_code=-1, timed_out=True)],
    )

    result = apply_and_validate_patch(
        tmp_path,
        _proposal(),
        approved=True,
        validation_commands=[["pytest"]],
    )

    assert result.passed is False
    assert result.checks[0].passed is False


def test_does_not_run_commands_if_patch_apply_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_apply(*args: Any, **kwargs: Any) -> PatchApplyResult:
        raise PatchApplyError("apply failed")

    def fake_run_command(*args: Any, **kwargs: Any) -> CommandResult:
        raise AssertionError("run_command should not be called")

    monkeypatch.setattr(
        "repopilot.validation.pipeline.apply_patch_proposal",
        fake_apply,
    )
    monkeypatch.setattr("repopilot.validation.pipeline.run_command", fake_run_command)

    with pytest.raises(PatchApplyError, match="apply failed"):
        apply_and_validate_patch(tmp_path, _proposal(), approved=True)


def test_uses_run_command_rather_than_subprocess_directly(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_apply(monkeypatch)
    called = False

    def fake_run_command(*args: Any, **kwargs: Any) -> CommandResult:
        nonlocal called
        called = True
        return _command_result(args[1], return_code=0)

    monkeypatch.setattr("repopilot.validation.pipeline.run_command", fake_run_command)

    apply_and_validate_patch(
        tmp_path,
        _proposal(),
        approved=True,
        validation_commands=[["pytest"]],
    )

    assert called is True


def test_respects_custom_validation_commands(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_apply(monkeypatch)
    calls: list[tuple[list[str], list[list[str]]]] = []

    def fake_run_command(*args: Any, **kwargs: Any) -> CommandResult:
        command = args[1]
        calls.append((command, kwargs["allowed_commands"]))
        return _command_result(command, return_code=0)

    monkeypatch.setattr("repopilot.validation.pipeline.run_command", fake_run_command)

    custom_commands = [["ruff", "format", "--check", "."]]
    apply_and_validate_patch(
        tmp_path,
        _proposal(),
        approved=True,
        validation_commands=custom_commands,
    )

    assert calls == [(custom_commands[0], custom_commands)]


def test_default_commands_are_pytest_and_ruff_check(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_apply(monkeypatch)
    commands: list[list[str]] = []

    def fake_run_command(*args: Any, **kwargs: Any) -> CommandResult:
        command = args[1]
        commands.append(command)
        return _command_result(command, return_code=0)

    monkeypatch.setattr("repopilot.validation.pipeline.run_command", fake_run_command)

    apply_and_validate_patch(tmp_path, _proposal(), approved=True)

    assert commands == [["pytest"], ["ruff", "check", "."]]


def test_propagates_patch_apply_errors_clearly(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_apply(*args: Any, **kwargs: Any) -> PatchApplyResult:
        raise PatchApplyError("content mismatch")

    monkeypatch.setattr(
        "repopilot.validation.pipeline.apply_patch_proposal",
        fake_apply,
    )

    with pytest.raises(PatchApplyError, match="content mismatch"):
        apply_and_validate_patch(tmp_path, _proposal(), approved=True)


def test_returns_deterministic_structured_result(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_apply(monkeypatch)

    def fake_run_command(*args: Any, **kwargs: Any) -> CommandResult:
        return _command_result(args[1], return_code=0)

    monkeypatch.setattr("repopilot.validation.pipeline.run_command", fake_run_command)

    first = apply_and_validate_patch(
        tmp_path,
        _proposal(),
        approved=True,
        validation_commands=[["pytest"]],
    )
    second = apply_and_validate_patch(
        tmp_path,
        _proposal(),
        approved=True,
        validation_commands=[["pytest"]],
    )

    assert first.model_dump() == second.model_dump()


def _patch_apply(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_apply(*args: Any, **kwargs: Any) -> PatchApplyResult:
        return _apply_result()

    monkeypatch.setattr(
        "repopilot.validation.pipeline.apply_patch_proposal",
        fake_apply,
    )


def _patch_run_command(
    monkeypatch: pytest.MonkeyPatch,
    results: list[CommandResult],
) -> None:
    remaining_results = list(results)

    def fake_run_command(*args: Any, **kwargs: Any) -> CommandResult:
        return remaining_results.pop(0)

    monkeypatch.setattr("repopilot.validation.pipeline.run_command", fake_run_command)


def _apply_result() -> PatchApplyResult:
    return PatchApplyResult(
        applied_files=[
            PatchAppliedFile(
                path="src/auth.py",
                old_content="old\n",
                new_content="new\n",
                changed=True,
            )
        ],
        changed_file_count=1,
    )


def _command_result(
    command: list[str],
    *,
    return_code: int,
    timed_out: bool = False,
) -> CommandResult:
    return CommandResult(
        command=command,
        return_code=return_code,
        stdout="stdout",
        stderr="stderr",
        timed_out=timed_out,
    )


def _proposal() -> PatchProposal:
    return PatchProposal(
        summary="Update auth file.",
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
