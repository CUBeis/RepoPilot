from typing import Any

from pydantic import BaseModel, Field, field_validator

from repopilot.patching.models import PatchProposal
from repopilot.schemas.apply import AppliedFileResponse
from repopilot.schemas.validation import ValidationCheckResponse


class RepairApplyRequest(BaseModel):
    """Request body for applying an approved repair proposal."""

    root_path: str = Field(min_length=1)
    repair_proposal: PatchProposal
    approved: bool
    run_validation: bool = False
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


class RepairValidationResponse(BaseModel):
    """Validation result summary returned after applying a repair."""

    checks: list[ValidationCheckResponse]
    passed: bool


class RepairApplyResponse(BaseModel):
    """Safe API response for approval-gated repair application."""

    changed_file_count: int = Field(ge=0)
    applied_files: list[AppliedFileResponse]
    validation: RepairValidationResponse | None
