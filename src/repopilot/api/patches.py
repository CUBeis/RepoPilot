from fastapi import APIRouter, HTTPException

from repopilot.context import ContextBuildError, build_repository_context
from repopilot.patching import (
    PatchProposal,
    PatchProposalError,
    create_patch_proposal,
)
from repopilot.planning import (
    ImplementationPlan,
    PlanningError,
    create_implementation_plan,
)
from repopilot.repository import RepositoryScanError
from repopilot.schemas.patches import (
    PatchPreviewRequest,
    PatchPreviewResponse,
    PatchProposalPreviewResponse,
    ProposedFileChangePreview,
)
from repopilot.schemas.planning import ImplementationPlanResponse
from repopilot.tools import FileToolError, read_text_file
from repopilot.tools.models import FileReadResult

router = APIRouter(tags=["patches"])


@router.post(
    "/repositories/patch-preview",
    response_model=PatchPreviewResponse,
)
def preview_repository_patch(
    request: PatchPreviewRequest,
) -> PatchPreviewResponse:
    """Return a deterministic approval-gated patch proposal preview."""

    try:
        context = build_repository_context(
            request.root_path,
            request.issue,
            top_k=request.top_k,
        )
        plan = create_implementation_plan(request.issue, context)
        file_reads = _read_relevant_files(
            root_path=request.root_path,
            relevant_files=plan.relevant_files,
        )
        proposal = create_patch_proposal(plan, file_reads)
    except (
        ContextBuildError,
        FileToolError,
        PatchProposalError,
        PlanningError,
        RepositoryScanError,
    ) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    return PatchPreviewResponse(
        root_name=context.root_name,
        issue=request.issue,
        scanned_file_count=context.scanned_file_count,
        skipped_file_count=context.skipped_file_count,
        total_chunks=context.total_chunks,
        retrieved_count=len(context.retrieved_chunks),
        plan=_plan_to_response(plan),
        proposal=_proposal_to_response(
            proposal,
            max_preview_chars=request.max_preview_chars,
        ),
    )


def _read_relevant_files(
    *,
    root_path: str,
    relevant_files: list[str],
) -> list[FileReadResult]:
    return [
        read_text_file(root_path, relevant_file) for relevant_file in relevant_files
    ]


def _plan_to_response(plan: ImplementationPlan) -> ImplementationPlanResponse:
    return ImplementationPlanResponse.model_validate(plan.model_dump())


def _proposal_to_response(
    proposal: PatchProposal,
    *,
    max_preview_chars: int,
) -> PatchProposalPreviewResponse:
    return PatchProposalPreviewResponse(
        summary=proposal.summary,
        target_files=proposal.target_files,
        changes=[
            ProposedFileChangePreview(
                path=change.path,
                reason=change.reason,
                start_line=change.start_line,
                end_line=change.end_line,
                original_preview=_truncate_preview(
                    change.original_content,
                    max_preview_chars,
                ),
                proposed_preview=_truncate_preview(
                    change.proposed_content,
                    max_preview_chars,
                ),
            )
            for change in proposal.changes
        ],
        risks=proposal.risks,
        requires_approval=True,
    )


def _truncate_preview(text: str, max_preview_chars: int) -> str:
    return text[:max_preview_chars]
