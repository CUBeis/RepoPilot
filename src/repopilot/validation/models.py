from pydantic import BaseModel, Field

from repopilot.patching.models import PatchApplyResult
from repopilot.tools.models import CommandResult


class ValidationCheck(BaseModel):
    """One validation command result."""

    name: str
    command: list[str]
    result: CommandResult
    passed: bool


class PatchValidationResult(BaseModel):
    """Structured result for applying and validating a patch proposal."""

    apply_result: PatchApplyResult
    checks: list[ValidationCheck]
    passed: bool


class FailedCheckSummary(BaseModel):
    """Compact summary for one failed validation check."""

    name: str
    command: list[str]
    return_code: int
    timed_out: bool
    stdout_excerpt: str
    stderr_excerpt: str


class FailureAnalysis(BaseModel):
    """Structured analysis of a patch validation result."""

    passed: bool
    failed_check_count: int = Field(ge=0)
    failed_checks: list[FailedCheckSummary]
    summary: str
    needs_self_correction: bool
