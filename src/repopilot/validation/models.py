from pydantic import BaseModel

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
