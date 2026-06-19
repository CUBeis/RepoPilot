from fastapi import APIRouter

from repopilot.schemas.repair_reports import (
    RepairApplyReportRequest,
    RepairApplyReportResponse,
    RepairReportFailedCheckResponse,
)

router = APIRouter(tags=["reports"])


@router.post(
    "/reports/repair-apply-result",
    response_model=RepairApplyReportResponse,
)
def create_repair_apply_result_report(
    request: RepairApplyReportRequest,
) -> RepairApplyReportResponse:
    """Return a read-only report for a supplied repair apply result."""

    repair_result = request.repair_result
    validation = repair_result.validation
    validation_ran = validation is not None
    validation_passed = None if validation is None else validation.passed
    failed_checks = (
        []
        if validation is None
        else [
            RepairReportFailedCheckResponse(
                name=check.name,
                command=check.command,
                return_code=check.return_code,
                timed_out=check.timed_out,
            )
            for check in validation.checks
            if not check.passed
        ]
    )
    changed_files = [
        applied_file.path
        for applied_file in repair_result.applied_files
        if applied_file.changed
    ]
    status = _resolve_status(
        validation_ran=validation_ran,
        validation_passed=validation_passed,
    )

    response = RepairApplyReportResponse(
        status=status,
        issue=request.issue,
        summary=request.repair_summary,
        changed_file_count=repair_result.changed_file_count,
        changed_files=changed_files,
        validation_ran=validation_ran,
        validation_passed=validation_passed,
        validation_check_count=0 if validation is None else len(validation.checks),
        failed_check_count=len(failed_checks),
        failed_checks=failed_checks,
        markdown_summary="",
    )
    return response.model_copy(
        update={"markdown_summary": _build_markdown_summary(response)}
    )


def _resolve_status(
    *,
    validation_ran: bool,
    validation_passed: bool | None,
) -> str:
    if not validation_ran:
        return "repair_applied"
    if validation_passed:
        return "repair_applied_validation_passed"
    return "repair_applied_validation_failed"


def _build_markdown_summary(report: RepairApplyReportResponse) -> str:
    lines = [
        "# RepoPilot Repair Apply Report",
        "",
        f"**Status:** {report.status}",
        f"**Issue:** {report.issue}",
        f"**Repair Summary:** {report.summary}",
        f"**Changed File Count:** {report.changed_file_count}",
        "",
        "## Changed Files",
    ]

    if report.changed_files:
        lines.extend(f"- `{path}`" for path in report.changed_files)
    else:
        lines.append("- None")

    lines.extend(
        [
            "",
            "## Validation",
        ]
    )
    if not report.validation_ran:
        lines.append("Validation was not run.")
    else:
        validation_status = "passed" if report.validation_passed else "failed"
        lines.append(f"Validation {validation_status}.")
        lines.append(f"Checks run: {report.validation_check_count}")

    if report.failed_checks:
        lines.extend(["", "## Failed Checks"])
        lines.extend(
            (
                f"- `{check.name}` returned {check.return_code}"
                f" for `{' '.join(check.command)}`"
            )
            for check in report.failed_checks
        )

    return "\n".join(lines)
