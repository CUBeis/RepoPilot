from fastapi import APIRouter, HTTPException

from repopilot.context import ContextBuildError, build_repository_context
from repopilot.planning import PlanningError, create_implementation_plan
from repopilot.repository import RepositoryScanError
from repopilot.schemas.planning import (
    ImplementationPlanResponse,
    PlanningPreviewRequest,
    PlanningPreviewResponse,
    PlanStepResponse,
)

router = APIRouter(tags=["planning"])


@router.post(
    "/repositories/plan-preview",
    response_model=PlanningPreviewResponse,
)
def preview_repository_plan(
    request: PlanningPreviewRequest,
) -> PlanningPreviewResponse:
    """Return a deterministic implementation plan preview for a repository issue."""

    try:
        context = build_repository_context(
            request.root_path,
            request.issue,
            top_k=request.top_k,
        )
        plan = create_implementation_plan(request.issue, context)
    except (ContextBuildError, PlanningError, RepositoryScanError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    return PlanningPreviewResponse(
        root_name=context.root_name,
        issue=request.issue,
        scanned_file_count=context.scanned_file_count,
        skipped_file_count=context.skipped_file_count,
        total_chunks=context.total_chunks,
        retrieved_count=len(context.retrieved_chunks),
        plan=ImplementationPlanResponse(
            objective=plan.objective,
            relevant_files=plan.relevant_files,
            steps=[
                PlanStepResponse(
                    order=step.order,
                    description=step.description,
                    target_files=step.target_files,
                )
                for step in plan.steps
            ],
            risks=plan.risks,
            assumptions=plan.assumptions,
            confidence=plan.confidence,
        ),
    )
