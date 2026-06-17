from pydantic import BaseModel, Field

from repopilot.patching.models import PatchProposal
from repopilot.validation.models import FailureAnalysis, PatchValidationResult


class SelfCorrectionAttempt(BaseModel):
    """One validation attempt in a self-correction loop."""

    attempt_number: int = Field(ge=1)
    proposal: PatchProposal
    validation_result: PatchValidationResult
    failure_analysis: FailureAnalysis


class SelfCorrectionResult(BaseModel):
    """Structured result for a bounded self-correction loop."""

    attempts: list[SelfCorrectionAttempt]
    final_passed: bool
    stopped_reason: str
