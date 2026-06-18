from pydantic import BaseModel, Field, field_validator

from repopilot.patching.models import PatchProposal


class PatchApplyRequest(BaseModel):
    """Request body for approval-gated patch application."""

    root_path: str = Field(min_length=1)
    proposal: PatchProposal
    approved: bool

    @field_validator("root_path")
    @classmethod
    def root_path_must_not_be_blank(cls, value: str) -> str:
        cleaned_value = value.strip()
        if not cleaned_value:
            raise ValueError("root_path must not be empty")
        return cleaned_value


class AppliedFileResponse(BaseModel):
    """Safe API summary for one applied file."""

    path: str
    changed: bool


class PatchApplyResponse(BaseModel):
    """Safe API response for approval-gated patch application."""

    changed_file_count: int = Field(ge=0)
    applied_files: list[AppliedFileResponse]
