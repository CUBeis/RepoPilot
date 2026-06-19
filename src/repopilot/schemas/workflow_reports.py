from pydantic import BaseModel, Field, field_validator

from repopilot.schemas.analysis import FailureAnalysisResponse
from repopilot.schemas.patches import PatchProposalPreviewResponse
from repopilot.schemas.planning import ImplementationPlanResponse
from repopilot.schemas.repair_apply import RepairApplyResponse
from repopilot.schemas.repair_reports import RepairApplyReportResponse
from repopilot.schemas.repairs import RepairApprovalApiResponse
from repopilot.schemas.validation import ApplyAndValidateResponse


class WorkflowReportRequest(BaseModel):
    """Request body for generating a unified workflow report."""

    issue: str = Field(min_length=1)
    plan: ImplementationPlanResponse | None = None
    patch_proposal: PatchProposalPreviewResponse | None = None
    apply_result: RepairApplyResponse | None = None
    validation_result: ApplyAndValidateResponse | None = None
    failure_analysis: FailureAnalysisResponse | None = None
    repair_approval: RepairApprovalApiResponse | None = None
    repair_apply_report: RepairApplyReportResponse | None = None

    @field_validator("issue")
    @classmethod
    def issue_must_not_be_blank(cls, value: str) -> str:
        cleaned_value = value.strip()
        if not cleaned_value:
            raise ValueError("issue must not be empty")
        return cleaned_value


class WorkflowReportResponse(BaseModel):
    """PR-ready read-only summary for supplied workflow payloads."""

    status: str
    issue: str
    summary: str
    planned_files: list[str]
    proposed_files: list[str]
    changed_files: list[str]
    validation_ran: bool
    validation_passed: bool | None
    failed_check_count: int = Field(ge=0)
    repair_proposed: bool
    repair_applied: bool
    approval_required: bool
    markdown_summary: str
