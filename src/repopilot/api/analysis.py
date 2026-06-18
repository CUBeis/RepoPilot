from fastapi import APIRouter

from repopilot.schemas.analysis import (
    FailedCheckSummaryResponse,
    FailureAnalysisRequest,
    FailureAnalysisResponse,
)
from repopilot.validation import analyze_validation_result

router = APIRouter(tags=["analysis"])


@router.post(
    "/validation/analyze-failures",
    response_model=FailureAnalysisResponse,
)
def analyze_validation_failures(
    request: FailureAnalysisRequest,
) -> FailureAnalysisResponse:
    """Return structured failure analysis for a validation result."""

    analysis = analyze_validation_result(
        request.validation_result,
        max_excerpt_chars=request.max_excerpt_chars,
    )

    return FailureAnalysisResponse(
        passed=analysis.passed,
        failed_check_count=analysis.failed_check_count,
        failed_checks=[
            FailedCheckSummaryResponse(
                name=failed_check.name,
                command=failed_check.command,
                return_code=failed_check.return_code,
                timed_out=failed_check.timed_out,
                stdout_excerpt=failed_check.stdout_excerpt,
                stderr_excerpt=failed_check.stderr_excerpt,
            )
            for failed_check in analysis.failed_checks
        ],
        summary=analysis.summary,
        needs_self_correction=analysis.needs_self_correction,
    )
