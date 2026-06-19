from fastapi import APIRouter, HTTPException

from repopilot.patching import PatchApplyError, apply_patch_proposal
from repopilot.schemas.apply import AppliedFileResponse
from repopilot.schemas.repair_apply import (
    RepairApplyRequest,
    RepairApplyResponse,
    RepairValidationResponse,
)
from repopilot.schemas.validation import ValidationCheckResponse
from repopilot.tools import CommandToolError
from repopilot.validation import apply_and_validate_patch

OUTPUT_PREVIEW_CHARS = 2_000

router = APIRouter(tags=["repairs"])


@router.post(
    "/repairs/apply-approved",
    response_model=RepairApplyResponse,
)
def apply_approved_repair(request: RepairApplyRequest) -> RepairApplyResponse:
    """Apply a reviewed repair proposal after explicit approval."""

    try:
        if request.run_validation:
            validation_result = apply_and_validate_patch(
                request.root_path,
                request.repair_proposal,
                approved=request.approved,
                validation_commands=request.validation_commands,
                timeout_seconds=request.timeout_seconds,
            )
            apply_result = validation_result.apply_result
            validation = RepairValidationResponse(
                checks=[
                    ValidationCheckResponse(
                        name=check.name,
                        command=check.command,
                        return_code=check.result.return_code,
                        timed_out=check.result.timed_out,
                        stdout_preview=_truncate_output(check.result.stdout),
                        stderr_preview=_truncate_output(check.result.stderr),
                        passed=check.passed,
                    )
                    for check in validation_result.checks
                ],
                passed=validation_result.passed,
            )
        else:
            apply_result = apply_patch_proposal(
                request.root_path,
                request.repair_proposal,
                approved=request.approved,
            )
            validation = None
    except (CommandToolError, PatchApplyError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    return RepairApplyResponse(
        changed_file_count=apply_result.changed_file_count,
        applied_files=[
            AppliedFileResponse(
                path=applied_file.path,
                changed=applied_file.changed,
            )
            for applied_file in apply_result.applied_files
        ],
        validation=validation,
    )


def _truncate_output(output: str) -> str:
    return output[:OUTPUT_PREVIEW_CHARS]
