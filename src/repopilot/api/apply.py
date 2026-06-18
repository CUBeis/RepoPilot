from fastapi import APIRouter, HTTPException

from repopilot.patching import PatchApplyError, apply_patch_proposal
from repopilot.schemas.apply import (
    AppliedFileResponse,
    PatchApplyRequest,
    PatchApplyResponse,
)

router = APIRouter(tags=["patches"])


@router.post(
    "/patches/apply",
    response_model=PatchApplyResponse,
)
def apply_reviewed_patch(request: PatchApplyRequest) -> PatchApplyResponse:
    """Apply an already reviewed patch proposal after explicit approval."""

    try:
        result = apply_patch_proposal(
            request.root_path,
            request.proposal,
            approved=request.approved,
        )
    except PatchApplyError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    return PatchApplyResponse(
        changed_file_count=result.changed_file_count,
        applied_files=[
            AppliedFileResponse(
                path=applied_file.path,
                changed=applied_file.changed,
            )
            for applied_file in result.applied_files
        ],
    )
