from fastapi import APIRouter, HTTPException

from repopilot.agent import LLMRepairProposalError, prepare_repair_for_approval
from repopilot.llm import FakeLLMClient
from repopilot.schemas.repairs import (
    PatchProposalApiResponse,
    ProposedFileChangeApiResponse,
    RepairApprovalApiRequest,
    RepairApprovalApiResponse,
)

router = APIRouter(tags=["repairs"])


@router.post(
    "/repairs/approval-request",
    response_model=RepairApprovalApiResponse,
)
def create_repair_approval_request(
    request: RepairApprovalApiRequest,
) -> RepairApprovalApiResponse:
    """Generate a repair proposal and return it for human approval."""

    llm_client = FakeLLMClient(request.llm_response_json)
    try:
        approval_request = prepare_repair_for_approval(
            request.failed_attempt,
            request.file_reads,
            llm_client,
            model=request.model,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )
    except LLMRepairProposalError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    proposal = approval_request.repair_proposal.model_copy(
        update={"requires_approval": True}
    )

    return RepairApprovalApiResponse(
        approval_required=True,
        summary=approval_request.summary,
        repair_proposal=PatchProposalApiResponse(
            summary=proposal.summary,
            target_files=proposal.target_files,
            changes=[
                ProposedFileChangeApiResponse(
                    path=change.path,
                    reason=change.reason,
                    start_line=change.start_line,
                    end_line=change.end_line,
                    original_content=change.original_content,
                    proposed_content=change.proposed_content,
                )
                for change in proposal.changes
            ],
            risks=proposal.risks,
            requires_approval=True,
        ),
        failed_attempt_number=approval_request.failed_attempt.attempt_number,
    )
