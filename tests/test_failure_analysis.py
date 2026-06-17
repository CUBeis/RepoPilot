from pathlib import Path

import pytest

from repopilot.patching.models import PatchAppliedFile, PatchApplyResult
from repopilot.tools.models import CommandResult
from repopilot.validation import (
    PatchValidationResult,
    ValidationCheck,
    analyze_validation_result,
)


def test_returns_passed_analysis_for_successful_validation() -> None:
    validation_result = _validation_result(
        passed=True,
        checks=[
            _check("pytest", ["pytest"], return_code=0, passed=True),
        ],
    )

    analysis = analyze_validation_result(validation_result)

    assert analysis.passed is True
    assert analysis.failed_check_count == 0
    assert analysis.failed_checks == []
    assert analysis.needs_self_correction is False
    assert analysis.summary == (
        "Validation passed. No failed checks require self-correction."
    )


def test_detects_failed_command_checks() -> None:
    validation_result = _validation_result(
        passed=False,
        checks=[
            _check("pytest", ["pytest"], return_code=1, passed=False),
            _check("ruff check .", ["ruff", "check", "."], return_code=0, passed=True),
        ],
    )

    analysis = analyze_validation_result(validation_result)

    assert analysis.failed_check_count == 1
    assert analysis.failed_checks[0].name == "pytest"
    assert analysis.failed_checks[0].command == ["pytest"]
    assert analysis.failed_checks[0].return_code == 1
    assert "pytest exited with return code 1" in analysis.summary


def test_detects_timeout_checks() -> None:
    validation_result = _validation_result(
        passed=False,
        checks=[
            _check(
                "pytest",
                ["pytest"],
                return_code=-1,
                passed=False,
                timed_out=True,
            ),
        ],
    )

    analysis = analyze_validation_result(validation_result)

    assert analysis.failed_checks[0].timed_out is True
    assert "pytest timed out" in analysis.summary


def test_includes_stdout_and_stderr_excerpts() -> None:
    validation_result = _validation_result(
        passed=False,
        checks=[
            _check(
                "pytest",
                ["pytest"],
                return_code=1,
                passed=False,
                stdout="stdout details",
                stderr="stderr details",
            ),
        ],
    )

    analysis = analyze_validation_result(validation_result)

    failed_check = analysis.failed_checks[0]
    assert failed_check.stdout_excerpt == "stdout details"
    assert failed_check.stderr_excerpt == "stderr details"


def test_truncates_long_stdout_and_stderr_excerpts() -> None:
    validation_result = _validation_result(
        passed=False,
        checks=[
            _check(
                "pytest",
                ["pytest"],
                return_code=1,
                passed=False,
                stdout="a" * 20,
                stderr="b" * 20,
            ),
        ],
    )

    analysis = analyze_validation_result(validation_result, max_excerpt_chars=5)

    assert analysis.failed_checks[0].stdout_excerpt == "a" * 5
    assert analysis.failed_checks[0].stderr_excerpt == "b" * 5


def test_counts_failed_checks() -> None:
    validation_result = _validation_result(
        passed=False,
        checks=[
            _check("pytest", ["pytest"], return_code=1, passed=False),
            _check("ruff check .", ["ruff", "check", "."], return_code=1, passed=False),
        ],
    )

    analysis = analyze_validation_result(validation_result)

    assert analysis.failed_check_count == 2


def test_sets_needs_self_correction_correctly() -> None:
    failed_analysis = analyze_validation_result(
        _validation_result(
            passed=False,
            checks=[_check("pytest", ["pytest"], return_code=1, passed=False)],
        )
    )
    passed_analysis = analyze_validation_result(
        _validation_result(
            passed=True,
            checks=[_check("pytest", ["pytest"], return_code=0, passed=True)],
        )
    )

    assert failed_analysis.needs_self_correction is True
    assert passed_analysis.needs_self_correction is False


def test_produces_deterministic_output() -> None:
    validation_result = _validation_result(
        passed=False,
        checks=[_check("pytest", ["pytest"], return_code=1, passed=False)],
    )

    first = analyze_validation_result(validation_result)
    second = analyze_validation_result(validation_result)

    assert first.model_dump() == second.model_dump()


def test_does_not_run_commands(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_if_called(*args: object, **kwargs: object) -> None:
        raise AssertionError("run_command should not be called")

    monkeypatch.setattr("repopilot.tools.commands.run_command", fail_if_called)

    analysis = analyze_validation_result(
        _validation_result(
            passed=False,
            checks=[_check("pytest", ["pytest"], return_code=1, passed=False)],
        )
    )

    assert analysis.failed_check_count == 1


def test_does_not_mutate_files(tmp_path: Path) -> None:
    target_file = tmp_path / "result.txt"
    target_file.write_text("unchanged\n", encoding="utf-8")

    analyze_validation_result(
        _validation_result(
            passed=False,
            checks=[_check("pytest", ["pytest"], return_code=1, passed=False)],
        )
    )

    assert target_file.read_text(encoding="utf-8") == "unchanged\n"


def _validation_result(
    *,
    passed: bool,
    checks: list[ValidationCheck],
) -> PatchValidationResult:
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
        checks=checks,
        passed=passed,
    )


def _check(
    name: str,
    command: list[str],
    *,
    return_code: int,
    passed: bool,
    stdout: str = "stdout",
    stderr: str = "stderr",
    timed_out: bool = False,
) -> ValidationCheck:
    return ValidationCheck(
        name=name,
        command=command,
        result=CommandResult(
            command=command,
            return_code=return_code,
            stdout=stdout,
            stderr=stderr,
            timed_out=timed_out,
        ),
        passed=passed,
    )
