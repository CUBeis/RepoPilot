from typing import Any

from pydantic import BaseModel, Field, field_validator

from repopilot.patching.models import PatchProposal
from repopilot.schemas.apply import AppliedFileResponse


class ApplyAndValidateRequest(BaseModel):
    """Request body for approval-gated apply-and-validate workflows."""

    root_path: str = Field(min_length=1)
    proposal: PatchProposal
    approved: bool
    validation_commands: list[list[str]] | None = None
    timeout_seconds: int = Field(default=30, ge=1, le=120)

    @field_validator("root_path")
    @classmethod
    def root_path_must_not_be_blank(cls, value: str) -> str:
        cleaned_value = value.strip()
        if not cleaned_value:
            raise ValueError("root_path must not be empty")
        return cleaned_value

    @field_validator("validation_commands", mode="before")
    @classmethod
    def validation_commands_must_be_non_empty(
        cls,
        value: Any,
    ) -> Any:
        if value is None:
            return None
        if not isinstance(value, list) or not value:
            raise ValueError(
                "validation_commands must be a non-empty list of commands"
            )

        for command in value:
            if not isinstance(command, list) or not command:
                raise ValueError(
                    "each validation command must be a non-empty list of strings"
                )
            if not all(isinstance(part, str) and part for part in command):
                raise ValueError(
                    "validation command parts must be non-empty strings"
                )

        return value


class ValidationCheckResponse(BaseModel):
    """Bounded API summary for one validation command."""

    name: str
    command: list[str]
    return_code: int
    timed_out: bool
    stdout_preview: str
    stderr_preview: str
    passed: bool


class ApplyAndValidateResponse(BaseModel):
    """Safe API response for apply-and-validate workflows."""

    changed_file_count: int = Field(ge=0)
    applied_files: list[AppliedFileResponse]
    checks: list[ValidationCheckResponse]
    passed: bool
