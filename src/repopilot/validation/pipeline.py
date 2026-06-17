from __future__ import annotations

from pathlib import Path

from repopilot.patching import apply_patch_proposal
from repopilot.patching.models import PatchProposal
from repopilot.tools import run_command
from repopilot.validation.models import PatchValidationResult, ValidationCheck

DEFAULT_VALIDATION_COMMANDS = [
    ["pytest"],
    ["ruff", "check", "."],
]


def apply_and_validate_patch(
    root_path: str | Path,
    proposal: PatchProposal,
    *,
    approved: bool,
    validation_commands: list[list[str]] | None = None,
    timeout_seconds: int = 30,
) -> PatchValidationResult:
    """Apply an approved patch proposal, then run validation commands."""

    commands = _resolve_validation_commands(validation_commands)
    apply_result = apply_patch_proposal(root_path, proposal, approved=approved)

    checks = [
        _run_validation_check(
            root_path=root_path,
            command=command,
            allowed_commands=commands,
            timeout_seconds=timeout_seconds,
        )
        for command in commands
    ]

    return PatchValidationResult(
        apply_result=apply_result,
        checks=checks,
        passed=all(check.passed for check in checks),
    )


def _run_validation_check(
    *,
    root_path: str | Path,
    command: list[str],
    allowed_commands: list[list[str]],
    timeout_seconds: int,
) -> ValidationCheck:
    result = run_command(
        root_path,
        command,
        timeout_seconds=timeout_seconds,
        allowed_commands=allowed_commands,
    )
    return ValidationCheck(
        name=" ".join(command),
        command=list(command),
        result=result,
        passed=result.return_code == 0 and not result.timed_out,
    )


def _resolve_validation_commands(
    validation_commands: list[list[str]] | None,
) -> list[list[str]]:
    raw_commands = (
        DEFAULT_VALIDATION_COMMANDS
        if validation_commands is None
        else validation_commands
    )
    return [list(command) for command in raw_commands]
