from fastapi import APIRouter, HTTPException

from repopilot.patching import PatchApplyError
from repopilot.schemas.apply import AppliedFileResponse
from repopilot.schemas.validation import (
    ApplyAndValidateRequest,
    ApplyAndValidateResponse,
    ValidationCheckResponse,
)
from repopilot.tools import CommandToolError
from repopilot.validation import apply_and_validate_patch

OUTPUT_PREVIEW_CHARS = 2_000

router = APIRouter(tags=["validation"])


@router.post(
    "/patches/apply-and-validate",
    response_model=ApplyAndValidateResponse,
)
def apply_and_validate_reviewed_patch(
    request: ApplyAndValidateRequest,
) -> ApplyAndValidateResponse:
    """Apply an approved patch proposal and run allowlisted validation commands."""

    try:
        result = apply_and_validate_patch(
            request.root_path,
            request.proposal,
            approved=request.approved,
            validation_commands=request.validation_commands,
            timeout_seconds=request.timeout_seconds,
        )
    except (CommandToolError, PatchApplyError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    return ApplyAndValidateResponse(
        changed_file_count=result.apply_result.changed_file_count,
        applied_files=[
            AppliedFileResponse(
                path=applied_file.path,
                changed=applied_file.changed,
            )
            for applied_file in result.apply_result.applied_files
        ],
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
            for check in result.checks
        ],
        passed=result.passed,
    )


def _truncate_output(output: str) -> str:
    return output[:OUTPUT_PREVIEW_CHARS]
