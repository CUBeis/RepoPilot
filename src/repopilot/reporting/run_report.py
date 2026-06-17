from __future__ import annotations

from repopilot.agent.models import RepairApprovalRequest, SelfCorrectionResult
from repopilot.patching.models import PatchProposal
from repopilot.planning.models import ImplementationPlan
from repopilot.reporting.models import AgentRunReport
from repopilot.validation.models import FailureAnalysis, PatchValidationResult

STATUS_ISSUE_RECEIVED = "issue_received"
STATUS_PLANNED = "planned"
STATUS_PROPOSAL_READY = "proposal_ready"
STATUS_VALIDATED = "validated"
STATUS_VALIDATION_FAILED = "validation_failed"
STATUS_REPAIR_READY_FOR_APPROVAL = "repair_ready_for_approval"
STATUS_SELF_CORRECTION_COMPLETE = "self_correction_complete"
STATUS_SELF_CORRECTION_FAILED = "self_correction_failed"


def create_agent_run_report(
    *,
    issue: str,
    plan: ImplementationPlan | None = None,
    patch_proposal: PatchProposal | None = None,
    validation_result: PatchValidationResult | None = None,
    failure_analysis: FailureAnalysis | None = None,
    self_correction_result: SelfCorrectionResult | None = None,
    repair_approval_request: RepairApprovalRequest | None = None,
) -> AgentRunReport:
    """Create a deterministic report from existing RepoPilot run artifacts."""

    cleaned_issue = issue.strip()
    if not cleaned_issue:
        raise ValueError("issue must not be empty")

    status = _determine_status(
        plan=plan,
        patch_proposal=patch_proposal,
        validation_result=validation_result,
        self_correction_result=self_correction_result,
        repair_approval_request=repair_approval_request,
    )
    planned_files = _planned_files(plan)
    proposed_files = _proposed_files(patch_proposal, repair_approval_request)
    changed_files = _changed_files(validation_result)
    validation_passed = (
        validation_result.passed if validation_result is not None else None
    )
    failed_checks = _failed_check_names(failure_analysis)
    approval_required = _approval_required(
        patch_proposal,
        repair_approval_request,
    )
    repair_proposed = repair_approval_request is not None
    stopped_reason = (
        self_correction_result.stopped_reason
        if self_correction_result is not None
        else None
    )
    summary = _build_summary(
        status=status,
        issue=cleaned_issue,
        plan=plan,
        patch_proposal=patch_proposal,
        validation_result=validation_result,
        failure_analysis=failure_analysis,
        self_correction_result=self_correction_result,
        repair_approval_request=repair_approval_request,
    )
    markdown_summary = _build_markdown_summary(
        issue=cleaned_issue,
        status=status,
        summary=summary,
        planned_files=planned_files,
        proposed_files=proposed_files,
        changed_files=changed_files,
        validation_passed=validation_passed,
        failed_checks=failed_checks,
        approval_required=approval_required,
        repair_proposed=repair_proposed,
        stopped_reason=stopped_reason,
    )

    return AgentRunReport(
        issue=cleaned_issue,
        status=status,
        summary=summary,
        planned_files=planned_files,
        proposed_files=proposed_files,
        changed_files=changed_files,
        validation_passed=validation_passed,
        failed_checks=failed_checks,
        approval_required=approval_required,
        repair_proposed=repair_proposed,
        stopped_reason=stopped_reason,
        markdown_summary=markdown_summary,
    )


def _determine_status(
    *,
    plan: ImplementationPlan | None,
    patch_proposal: PatchProposal | None,
    validation_result: PatchValidationResult | None,
    self_correction_result: SelfCorrectionResult | None,
    repair_approval_request: RepairApprovalRequest | None,
) -> str:
    if self_correction_result is not None:
        if self_correction_result.final_passed:
            return STATUS_SELF_CORRECTION_COMPLETE
        return STATUS_SELF_CORRECTION_FAILED

    if repair_approval_request is not None:
        return STATUS_REPAIR_READY_FOR_APPROVAL

    if validation_result is not None:
        if validation_result.passed:
            return STATUS_VALIDATED
        return STATUS_VALIDATION_FAILED

    if patch_proposal is not None and patch_proposal.requires_approval:
        return STATUS_PROPOSAL_READY

    if plan is not None:
        return STATUS_PLANNED

    return STATUS_ISSUE_RECEIVED


def _build_summary(
    *,
    status: str,
    issue: str,
    plan: ImplementationPlan | None,
    patch_proposal: PatchProposal | None,
    validation_result: PatchValidationResult | None,
    failure_analysis: FailureAnalysis | None,
    self_correction_result: SelfCorrectionResult | None,
    repair_approval_request: RepairApprovalRequest | None,
) -> str:
    if status == STATUS_SELF_CORRECTION_COMPLETE:
        return "Self-correction completed successfully."

    if status == STATUS_SELF_CORRECTION_FAILED:
        assert self_correction_result is not None
        return (
            "Self-correction did not pass validation. "
            f"Stopped reason: {self_correction_result.stopped_reason}."
        )

    if status == STATUS_REPAIR_READY_FOR_APPROVAL:
        assert repair_approval_request is not None
        return repair_approval_request.summary

    if status == STATUS_VALIDATED:
        assert validation_result is not None
        return (
            "Validation passed after applying "
            f"{validation_result.apply_result.changed_file_count} changed file(s)."
        )

    if status == STATUS_VALIDATION_FAILED:
        if failure_analysis is not None:
            return failure_analysis.summary
        return "Validation failed."

    if status == STATUS_PROPOSAL_READY:
        assert patch_proposal is not None
        return patch_proposal.summary

    if status == STATUS_PLANNED:
        assert plan is not None
        return plan.objective

    return f"Issue received: {issue}"


def _build_markdown_summary(
    *,
    issue: str,
    status: str,
    summary: str,
    planned_files: list[str],
    proposed_files: list[str],
    changed_files: list[str],
    validation_passed: bool | None,
    failed_checks: list[str],
    approval_required: bool,
    repair_proposed: bool,
    stopped_reason: str | None,
) -> str:
    lines = [
        "# RepoPilot Run Report",
        "",
        f"**Issue:** {issue}",
        f"**Status:** {status}",
        f"**Summary:** {summary}",
        "",
        "## Files",
        f"- Planned: {_format_list(planned_files)}",
        f"- Proposed: {_format_list(proposed_files)}",
        f"- Changed: {_format_list(changed_files)}",
        "",
        "## Validation",
        f"- Passed: {_format_optional_bool(validation_passed)}",
        f"- Failed checks: {_format_list(failed_checks)}",
        "",
        "## Approval",
        f"- Approval required: {_format_bool(approval_required)}",
        f"- Repair proposed: {_format_bool(repair_proposed)}",
        f"- Stopped reason: {stopped_reason or 'none'}",
    ]
    return "\n".join(lines)


def _planned_files(plan: ImplementationPlan | None) -> list[str]:
    if plan is None:
        return []
    return _unique(plan.relevant_files)


def _proposed_files(
    patch_proposal: PatchProposal | None,
    repair_approval_request: RepairApprovalRequest | None,
) -> list[str]:
    paths: list[str] = []

    if patch_proposal is not None:
        paths.extend(_proposal_paths(patch_proposal))

    if repair_approval_request is not None:
        paths.extend(_proposal_paths(repair_approval_request.repair_proposal))

    return _unique(paths)


def _proposal_paths(proposal: PatchProposal) -> list[str]:
    return [
        *proposal.target_files,
        *(change.path for change in proposal.changes),
    ]


def _changed_files(
    validation_result: PatchValidationResult | None,
) -> list[str]:
    if validation_result is None:
        return []

    return _unique(
        [
            applied_file.path
            for applied_file in validation_result.apply_result.applied_files
            if applied_file.changed
        ]
    )


def _failed_check_names(
    failure_analysis: FailureAnalysis | None,
) -> list[str]:
    if failure_analysis is None:
        return []

    return _unique(
        [failed_check.name for failed_check in failure_analysis.failed_checks]
    )


def _approval_required(
    patch_proposal: PatchProposal | None,
    repair_approval_request: RepairApprovalRequest | None,
) -> bool:
    proposal_requires_approval = (
        patch_proposal.requires_approval if patch_proposal is not None else False
    )
    repair_requires_approval = False

    if repair_approval_request is not None:
        repair_requires_approval = (
            repair_approval_request.approval_required
            or repair_approval_request.repair_proposal.requires_approval
        )

    return proposal_requires_approval or repair_requires_approval


def _format_list(values: list[str]) -> str:
    if not values:
        return "none"
    return ", ".join(values)


def _format_optional_bool(value: bool | None) -> str:
    if value is None:
        return "not run"
    return _format_bool(value)


def _format_bool(value: bool) -> str:
    return "yes" if value else "no"


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    unique_values: list[str] = []

    for value in values:
        if value not in seen:
            seen.add(value)
            unique_values.append(value)

    return unique_values
