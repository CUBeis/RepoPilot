from __future__ import annotations

from repopilot.agent.models import RepairApprovalRequest, SelfCorrectionAttempt
from repopilot.agent.repair import (
    DEFAULT_LLM_REPAIR_PROPOSER_MODEL,
    create_llm_repair_proposal,
)
from repopilot.llm.client import LLMClient
from repopilot.tools.models import FileReadResult


def prepare_repair_for_approval(
    failed_attempt: SelfCorrectionAttempt,
    file_reads: list[FileReadResult],
    llm_client: LLMClient,
    *,
    model: str = DEFAULT_LLM_REPAIR_PROPOSER_MODEL,
    temperature: float = 0.0,
    max_tokens: int | None = None,
) -> RepairApprovalRequest:
    """Generate a repair proposal and return it without applying anything."""

    repair_proposal = create_llm_repair_proposal(
        failed_attempt,
        file_reads,
        llm_client,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
    ).model_copy(update={"requires_approval": True})

    return RepairApprovalRequest(
        failed_attempt=failed_attempt,
        repair_proposal=repair_proposal,
        approval_required=True,
        summary=(
            "Approval required for repair proposal after failed attempt "
            f"{failed_attempt.attempt_number}: {repair_proposal.summary}"
        ),
    )
