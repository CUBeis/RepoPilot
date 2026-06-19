from fastapi import APIRouter

from repopilot.schemas.repair_apply import RepairApplyResponse
from repopilot.schemas.validation import ApplyAndValidateResponse
from repopilot.schemas.workflow_reports import (
    WorkflowReportRequest,
    WorkflowReportResponse,
)

router = APIRouter(tags=["reports"])


@router.post("/reports/workflow", response_model=WorkflowReportResponse)
def create_workflow_report(
    request: WorkflowReportRequest,
) -> WorkflowReportResponse:
    """Create a read-only report from supplied workflow payloads."""

    return build_workflow_report(request)


def build_workflow_report(
    request: WorkflowReportRequest,
) -> WorkflowReportResponse:
    """Build a deterministic workflow report without executing tools."""

    status = _resolve_status(request)
    validation_ran, validation_passed = _resolve_validation_state(request)
    response = WorkflowReportResponse(
        status=status,
        issue=request.issue,
        summary=_build_summary(issue=request.issue, status=status),
        planned_files=_planned_files(request),
        proposed_files=_proposed_files(request),
        changed_files=_changed_files(request),
        validation_ran=validation_ran,
        validation_passed=validation_passed,
        failed_check_count=_failed_check_count(request),
        repair_proposed=request.repair_approval is not None,
        repair_applied=(
            request.apply_result is not None
            or request.repair_apply_report is not None
        ),
        approval_required=_approval_required(request),
        markdown_summary="",
    )
    return response.model_copy(
        update={"markdown_summary": _build_markdown_summary(response)}
    )


def _resolve_status(request: WorkflowReportRequest) -> str:
    if request.repair_apply_report is not None:
        return request.repair_apply_report.status
    if request.repair_approval is not None:
        return "repair_waiting_for_approval"
    if (
        request.failure_analysis is not None
        and request.failure_analysis.needs_self_correction
    ):
        return "validation_failed_needs_repair"
    if request.validation_result is not None:
        return (
            "validation_passed"
            if request.validation_result.passed
            else "validation_failed"
        )
    if request.apply_result is not None:
        return "patch_applied"
    if request.patch_proposal is not None:
        return "patch_proposed"
    if request.plan is not None:
        return "planned"
    return "issue_received"


def _resolve_validation_state(
    request: WorkflowReportRequest,
) -> tuple[bool, bool | None]:
    if request.repair_apply_report is not None:
        return (
            request.repair_apply_report.validation_ran,
            request.repair_apply_report.validation_passed,
        )
    if request.validation_result is not None:
        return True, request.validation_result.passed
    if request.apply_result is not None and request.apply_result.validation is not None:
        return True, request.apply_result.validation.passed
    return False, None


def _planned_files(request: WorkflowReportRequest) -> list[str]:
    return [] if request.plan is None else list(request.plan.relevant_files)


def _proposed_files(request: WorkflowReportRequest) -> list[str]:
    proposed_files: list[str] = []
    if request.patch_proposal is not None:
        proposed_files.extend(request.patch_proposal.target_files)
    if request.repair_approval is not None:
        proposed_files.extend(request.repair_approval.repair_proposal.target_files)
    return _dedupe_preserving_order(proposed_files)


def _changed_files(request: WorkflowReportRequest) -> list[str]:
    if request.repair_apply_report is not None:
        return list(request.repair_apply_report.changed_files)
    if request.apply_result is not None:
        return _changed_files_from_repair_apply(request.apply_result)
    if request.validation_result is not None:
        return _changed_files_from_validation(request.validation_result)
    return []


def _changed_files_from_repair_apply(result: RepairApplyResponse) -> list[str]:
    return [
        applied_file.path
        for applied_file in result.applied_files
        if applied_file.changed
    ]


def _changed_files_from_validation(result: ApplyAndValidateResponse) -> list[str]:
    return [
        applied_file.path
        for applied_file in result.applied_files
        if applied_file.changed
    ]


def _failed_check_count(request: WorkflowReportRequest) -> int:
    if request.repair_apply_report is not None:
        return request.repair_apply_report.failed_check_count
    if request.failure_analysis is not None:
        return request.failure_analysis.failed_check_count
    if request.validation_result is not None:
        return sum(1 for check in request.validation_result.checks if not check.passed)
    if request.apply_result is not None and request.apply_result.validation is not None:
        return sum(
            1
            for check in request.apply_result.validation.checks
            if not check.passed
        )
    return 0


def _approval_required(request: WorkflowReportRequest) -> bool:
    if (
        request.repair_approval is not None
        and request.repair_approval.approval_required
    ):
        return True
    if request.patch_proposal is not None and request.patch_proposal.requires_approval:
        return True
    return False


def _build_summary(*, issue: str, status: str) -> str:
    return f"Workflow report for '{issue}' is currently {status}."


def _build_markdown_summary(report: WorkflowReportResponse) -> str:
    lines = [
        "# RepoPilot Workflow Report",
        "",
        f"**Status:** {report.status}",
        f"**Issue:** {report.issue}",
        f"**Summary:** {report.summary}",
        "",
        "## Planned Files",
    ]
    lines.extend(_markdown_file_list(report.planned_files))
    lines.extend(["", "## Proposed Files"])
    lines.extend(_markdown_file_list(report.proposed_files))
    lines.extend(["", "## Changed Files"])
    lines.extend(_markdown_file_list(report.changed_files))
    lines.extend(["", "## Validation"])
    if report.validation_ran:
        state = "passed" if report.validation_passed else "failed"
        lines.append(f"Validation {state}.")
    else:
        lines.append("Validation was not run.")
    lines.append(f"Failed checks: {report.failed_check_count}")
    lines.extend(["", "## Repair"])
    lines.append(f"Repair proposed: {report.repair_proposed}")
    lines.append(f"Repair applied: {report.repair_applied}")
    lines.append(f"Approval required: {report.approval_required}")
    return "\n".join(lines)


def _markdown_file_list(paths: list[str]) -> list[str]:
    if not paths:
        return ["- None"]
    return [f"- `{path}`" for path in paths]


def _dedupe_preserving_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            deduped.append(value)
    return deduped
