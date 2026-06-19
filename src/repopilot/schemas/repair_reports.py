from pydantic import BaseModel, Field, field_validator

from repopilot.schemas.repair_apply import RepairApplyResponse


class RepairApplyReportRequest(BaseModel):
    """Request body for summarizing a repair apply result."""

    issue: str = Field(min_length=1)
    repair_summary: str = Field(min_length=1)
    repair_result: RepairApplyResponse

    @field_validator("issue", "repair_summary")
    @classmethod
    def text_fields_must_not_be_blank(cls, value: str) -> str:
        cleaned_value = value.strip()
        if not cleaned_value:
            raise ValueError("value must not be empty")
        return cleaned_value


class RepairReportFailedCheckResponse(BaseModel):
    """Failure metadata for one validation check in a repair report."""

    name: str
    command: list[str]
    return_code: int
    timed_out: bool


class RepairApplyReportResponse(BaseModel):
    """Read-only report summary for a repair apply result."""

    status: str
    issue: str
    summary: str
    changed_file_count: int = Field(ge=0)
    changed_files: list[str]
    validation_ran: bool
    validation_passed: bool | None
    validation_check_count: int = Field(ge=0)
    failed_check_count: int = Field(ge=0)
    failed_checks: list[RepairReportFailedCheckResponse]
    markdown_summary: str
