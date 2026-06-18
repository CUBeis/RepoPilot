from pydantic import BaseModel, Field, field_validator

from repopilot.agent.models import SelfCorrectionAttempt
from repopilot.tools.models import FileReadResult


class RepairApprovalApiRequest(BaseModel):
    """Request body for generating a repair proposal approval request."""

    failed_attempt: SelfCorrectionAttempt
    file_reads: list[FileReadResult]
    llm_response_json: str = Field(min_length=1)
    model: str = Field(default="fake-repair-proposer", min_length=1)
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=None, gt=0)

    @field_validator("llm_response_json", "model")
    @classmethod
    def text_fields_must_not_be_blank(cls, value: str) -> str:
        cleaned_value = value.strip()
        if not cleaned_value:
            raise ValueError("value must not be empty")
        return cleaned_value


class ProposedFileChangeApiResponse(BaseModel):
    """API representation of one proposed repair file change."""

    path: str
    reason: str
    start_line: int = Field(ge=0)
    end_line: int = Field(ge=0)
    original_content: str
    proposed_content: str


class PatchProposalApiResponse(BaseModel):
    """API representation of an approval-gated repair proposal."""

    summary: str
    target_files: list[str]
    changes: list[ProposedFileChangeApiResponse]
    risks: list[str]
    requires_approval: bool


class RepairApprovalApiResponse(BaseModel):
    """Safe API response for repair proposal approval requests."""

    approval_required: bool
    summary: str
    repair_proposal: PatchProposalApiResponse
    failed_attempt_number: int = Field(ge=1)
