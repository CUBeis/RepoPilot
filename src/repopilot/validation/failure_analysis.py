from repopilot.validation.models import (
    FailedCheckSummary,
    FailureAnalysis,
    PatchValidationResult,
    ValidationCheck,
)

DEFAULT_EXCERPT_MAX_CHARS = 1000


def analyze_validation_result(
    result: PatchValidationResult,
    *,
    max_excerpt_chars: int = DEFAULT_EXCERPT_MAX_CHARS,
) -> FailureAnalysis:
    """Analyze validation output without rerunning commands or fixing failures."""

    if max_excerpt_chars < 0:
        raise ValueError("max_excerpt_chars must be greater than or equal to 0")

    failed_checks = [check for check in result.checks if not check.passed]
    if result.passed:
        return FailureAnalysis(
            passed=True,
            failed_check_count=0,
            failed_checks=[],
            summary="Validation passed. No failed checks require self-correction.",
            needs_self_correction=False,
        )

    failed_summaries = [
        _summarize_failed_check(
            check,
            max_excerpt_chars=max_excerpt_chars,
        )
        for check in failed_checks
    ]

    return FailureAnalysis(
        passed=False,
        failed_check_count=len(failed_summaries),
        failed_checks=failed_summaries,
        summary=_build_summary(failed_summaries),
        needs_self_correction=bool(failed_summaries),
    )


def _summarize_failed_check(
    check: ValidationCheck,
    *,
    max_excerpt_chars: int,
) -> FailedCheckSummary:
    return FailedCheckSummary(
        name=check.name,
        command=list(check.command),
        return_code=check.result.return_code,
        timed_out=check.result.timed_out,
        stdout_excerpt=_excerpt(check.result.stdout, max_excerpt_chars),
        stderr_excerpt=_excerpt(check.result.stderr, max_excerpt_chars),
    )


def _excerpt(text: str, max_chars: int) -> str:
    return text[:max_chars]


def _build_summary(failed_checks: list[FailedCheckSummary]) -> str:
    if not failed_checks:
        return "Validation did not pass, but no failed checks were reported."

    failed_descriptions = ", ".join(
        _describe_failed_check(check) for check in failed_checks
    )
    check_label = "check" if len(failed_checks) == 1 else "checks"
    return (
        f"Validation failed: {len(failed_checks)} {check_label} failed. "
        f"{failed_descriptions}."
    )


def _describe_failed_check(check: FailedCheckSummary) -> str:
    if check.timed_out:
        return f"{check.name} timed out"
    return f"{check.name} exited with return code {check.return_code}"
