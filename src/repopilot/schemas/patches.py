from pydantic import BaseModel, Field, field_validator

from repopilot.schemas.planning import ImplementationPlanResponse


class PatchPreviewRequest(BaseModel):
    """Request body for deterministic patch proposal previews."""

    root_path: str = Field(min_length=1)
    issue: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)
    max_preview_chars: int = Field(default=500, ge=50, le=2000)

    @field_validator("root_path", "issue")
    @classmethod
    def text_fields_must_not_be_blank(cls, value: str) -> str:
        cleaned_value = value.strip()
        if not cleaned_value:
            raise ValueError("value must not be empty")
        return cleaned_value


class ProposedFileChangePreview(BaseModel):
    """Bounded preview of a proposed file change."""

    path: str
    reason: str
    start_line: int = Field(ge=0)
    end_line: int = Field(ge=0)
    original_preview: str
    proposed_preview: str


class PatchProposalPreviewResponse(BaseModel):
    """Safe API representation of an approval-gated patch proposal."""

    summary: str
    target_files: list[str]
    changes: list[ProposedFileChangePreview]
    risks: list[str]
    requires_approval: bool = True


class PatchPreviewResponse(BaseModel):
    """Safe API response for deterministic patch proposal previews."""

    root_name: str
    issue: str
    scanned_file_count: int = Field(ge=0)
    skipped_file_count: int = Field(ge=0)
    total_chunks: int = Field(ge=0)
    retrieved_count: int = Field(ge=0)
    plan: ImplementationPlanResponse
    proposal: PatchProposalPreviewResponse
