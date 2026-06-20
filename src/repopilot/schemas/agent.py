from pydantic import BaseModel, Field, field_validator

from repopilot.schemas.patches import PatchProposalPreviewResponse
from repopilot.schemas.planning import ImplementationPlanResponse


class AgentPreviewRequest(BaseModel):
    """Request body for safe agent preview generation."""

    root_path: str = Field(min_length=1)
    issue: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)
    max_preview_chars: int = Field(default=1000, ge=100, le=5000)
    use_llm: bool = True

    @field_validator("root_path", "issue")
    @classmethod
    def text_fields_must_not_be_blank(cls, value: str) -> str:
        cleaned_value = value.strip()
        if not cleaned_value:
            raise ValueError("value must not be empty")
        return cleaned_value


class AgentPreviewResponse(BaseModel):
    """Preview-only response for an issue, plan, and optional patch proposal."""

    issue: str
    root_name: str
    scanned_file_count: int = Field(ge=0)
    retrieved_count: int = Field(ge=0)
    used_llm: bool
    plan: ImplementationPlanResponse
    patch_proposal: PatchProposalPreviewResponse | None
    markdown_summary: str
    safety_note: str
