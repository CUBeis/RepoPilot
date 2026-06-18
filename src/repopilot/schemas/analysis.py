from pydantic import BaseModel, Field

from repopilot.validation.models import PatchValidationResult


class FailureAnalysisRequest(BaseModel):
    """Request body for read-only validation failure analysis."""

    validation_result: PatchValidationResult
    max_excerpt_chars: int = Field(default=1000, ge=0, le=5000)


class FailedCheckSummaryResponse(BaseModel):
    """Safe API summary for one failed validation check."""

    name: str
    command: list[str]
    return_code: int
    timed_out: bool
    stdout_excerpt: str
    stderr_excerpt: str


class FailureAnalysisResponse(BaseModel):
    """Safe API response for validation failure analysis."""

    passed: bool
    failed_check_count: int = Field(ge=0)
    failed_checks: list[FailedCheckSummaryResponse]
    summary: str
    needs_self_correction: bool
