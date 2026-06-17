"""Patch proposal utilities."""

from repopilot.patching.applier import PatchApplyError, apply_patch_proposal
from repopilot.patching.llm_proposal import (
    LLMPatchProposalError,
    create_llm_patch_proposal,
)
from repopilot.patching.models import (
    PatchAppliedFile,
    PatchApplyResult,
    PatchProposal,
    ProposedFileChange,
)
from repopilot.patching.proposal import PatchProposalError, create_patch_proposal

__all__ = [
    "LLMPatchProposalError",
    "PatchAppliedFile",
    "PatchApplyError",
    "PatchApplyResult",
    "PatchProposal",
    "PatchProposalError",
    "ProposedFileChange",
    "apply_patch_proposal",
    "create_llm_patch_proposal",
    "create_patch_proposal",
]
