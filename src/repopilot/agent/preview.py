from __future__ import annotations

from pathlib import Path

from repopilot.context import build_repository_context
from repopilot.context.models import RepositoryContext
from repopilot.llm import create_configured_llm_client
from repopilot.patching import (
    PatchProposal,
    PatchProposalError,
    create_patch_proposal,
)
from repopilot.planning import (
    ImplementationPlan,
    LLMPlanningError,
    create_implementation_plan,
    create_llm_implementation_plan,
)
from repopilot.schemas.agent import AgentPreviewResponse
from repopilot.schemas.patches import (
    PatchProposalPreviewResponse,
    ProposedFileChangePreview,
)
from repopilot.schemas.planning import ImplementationPlanResponse
from repopilot.tools import FileToolError, read_text_file
from repopilot.tools.models import FileReadResult

AGENT_PREVIEW_SAFETY_NOTE = (
    "Preview only: RepoPilot built context, created a plan, and prepared a "
    "bounded patch proposal preview without applying patches, running commands, "
    "generating repairs, or writing files."
)


class AgentPreviewError(ValueError):
    """Raised when an agent preview cannot be prepared from valid inputs."""


def create_agent_preview(
    root_path: str | Path,
    issue: str,
    *,
    top_k: int = 5,
    max_preview_chars: int = 1000,
    use_llm: bool = True,
) -> AgentPreviewResponse:
    """Build a safe issue-to-plan preview with an optional patch proposal."""
    cleaned_issue = issue.strip()
    if not cleaned_issue:
        raise AgentPreviewError("issue must not be empty")

    context = build_repository_context(root_path, cleaned_issue, top_k=top_k)
    plan, used_llm, mode_label = _create_plan(
        issue=cleaned_issue,
        context=context,
        use_llm=use_llm,
    )
    patch_proposal = _try_create_patch_preview(
        root_path=root_path,
        plan=plan,
        max_preview_chars=max_preview_chars,
    )

    return AgentPreviewResponse(
        issue=cleaned_issue,
        root_name=context.root_name,
        scanned_file_count=context.scanned_file_count,
        retrieved_count=len(context.retrieved_chunks),
        used_llm=used_llm,
        plan=_plan_to_response(plan),
        patch_proposal=patch_proposal,
        markdown_summary=_build_markdown_summary(
            issue=cleaned_issue,
            context=context,
            plan=plan,
            patch_proposal=patch_proposal,
            mode_label=mode_label,
        ),
        safety_note=AGENT_PREVIEW_SAFETY_NOTE,
    )


def _create_plan(
    *,
    issue: str,
    context: RepositoryContext,
    use_llm: bool,
) -> tuple[ImplementationPlan, bool, str]:
    if not use_llm:
        plan = create_implementation_plan(issue, context)
        return plan, False, "deterministic planning"

    llm_client = create_configured_llm_client()
    model = getattr(llm_client, "model", "configured-llm")
    try:
        plan = create_llm_implementation_plan(
            issue,
            context,
            llm_client,
            model=model,
            temperature=0.0,
        )
    except LLMPlanningError:
        fallback_plan = create_implementation_plan(issue, context)
        return fallback_plan, False, "deterministic fallback after invalid LLM plan"

    return plan, True, f"{_provider_label(llm_client)} LLM-backed planning"


def _try_create_patch_preview(
    *,
    root_path: str | Path,
    plan: ImplementationPlan,
    max_preview_chars: int,
) -> PatchProposalPreviewResponse | None:
    if not plan.relevant_files:
        return None

    try:
        file_reads = _read_relevant_files(
            root_path=root_path,
            relevant_files=plan.relevant_files,
        )
        proposal = create_patch_proposal(plan, file_reads)
    except (FileToolError, PatchProposalError):
        return None

    return _proposal_to_response(proposal, max_preview_chars=max_preview_chars)


def _read_relevant_files(
    *,
    root_path: str | Path,
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


def _build_markdown_summary(
    *,
    issue: str,
    context: RepositoryContext,
    plan: ImplementationPlan,
    patch_proposal: PatchProposalPreviewResponse | None,
    mode_label: str,
) -> str:
    planned_files = _format_paths(plan.relevant_files)
    proposal_status = (
        "ready for review" if patch_proposal is not None else "not created"
    )

    return "\n".join(
        [
            "# RepoPilot Agent Preview",
            "",
            f"## Issue\n{issue}",
            "",
            f"## Repository\n{context.root_name}",
            "",
            f"## Mode\n{mode_label}",
            "",
            "## Context",
            f"- Scanned files: {context.scanned_file_count}",
            f"- Retrieved chunks: {len(context.retrieved_chunks)}",
            "",
            "## Plan",
            f"- Objective: {plan.objective}",
            f"- Confidence: {plan.confidence}",
            f"- Relevant files: {planned_files}",
            "",
            "## Patch Proposal",
            f"- Status: {proposal_status}",
            "",
            "## Safety",
            AGENT_PREVIEW_SAFETY_NOTE,
        ]
    )


def _format_paths(paths: list[str]) -> str:
    if not paths:
        return "none"
    return ", ".join(paths)


def _provider_label(llm_client: object) -> str:
    client_name = type(llm_client).__name__.lower()
    if "openai" in client_name:
        return "OpenAI"
    if "openrouter" in client_name:
        return "OpenRouter"
    return "Configured provider"
