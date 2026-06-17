from __future__ import annotations

from pathlib import Path

from repopilot.agent.models import SelfCorrectionAttempt, SelfCorrectionResult
from repopilot.patching.models import PatchProposal
from repopilot.validation import analyze_validation_result, apply_and_validate_patch

STOPPED_VALIDATION_PASSED = "validation_passed"
STOPPED_MAX_ATTEMPTS_REACHED = "max_attempts_reached"
STOPPED_NO_REPAIR_PROPOSAL = "no_repair_proposal_available"


def run_self_correction_loop(
    root_path: str | Path,
    initial_proposal: PatchProposal,
    *,
    approved: bool,
    repair_proposals: list[PatchProposal] | None = None,
    max_attempts: int = 2,
    validation_commands: list[list[str]] | None = None,
    timeout_seconds: int = 30,
) -> SelfCorrectionResult:
    """Validate proposals in order without generating new repairs internally."""

    if max_attempts < 1:
        raise ValueError("max_attempts must be greater than or equal to 1")

    proposals = [initial_proposal, *(repair_proposals or [])]
    attempts: list[SelfCorrectionAttempt] = []

    for proposal in proposals[:max_attempts]:
        attempt_number = len(attempts) + 1
        validation_result = apply_and_validate_patch(
            root_path,
            proposal,
            approved=approved,
            validation_commands=validation_commands,
            timeout_seconds=timeout_seconds,
        )
        failure_analysis = analyze_validation_result(validation_result)
        attempts.append(
            SelfCorrectionAttempt(
                attempt_number=attempt_number,
                proposal=proposal,
                validation_result=validation_result,
                failure_analysis=failure_analysis,
            )
        )

        if validation_result.passed:
            return SelfCorrectionResult(
                attempts=attempts,
                final_passed=True,
                stopped_reason=STOPPED_VALIDATION_PASSED,
            )

        if attempt_number >= max_attempts:
            return SelfCorrectionResult(
                attempts=attempts,
                final_passed=False,
                stopped_reason=STOPPED_MAX_ATTEMPTS_REACHED,
            )

    return SelfCorrectionResult(
        attempts=attempts,
        final_passed=False,
        stopped_reason=STOPPED_NO_REPAIR_PROPOSAL,
    )
