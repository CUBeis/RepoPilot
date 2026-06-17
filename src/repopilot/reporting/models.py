from pydantic import BaseModel


class AgentRunReport(BaseModel):
    """Structured summary of a RepoPilot agent run."""

    issue: str
    status: str
    summary: str
    planned_files: list[str]
    proposed_files: list[str]
    changed_files: list[str]
    validation_passed: bool | None
    failed_checks: list[str]
    approval_required: bool
    repair_proposed: bool
    stopped_reason: str | None
    markdown_summary: str
