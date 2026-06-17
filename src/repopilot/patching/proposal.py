from repopilot.patching.models import PatchProposal, ProposedFileChange
from repopilot.planning.models import ImplementationPlan
from repopilot.tools.models import FileReadResult


class PatchProposalError(ValueError):
    """Raised when a patch proposal cannot be created safely."""


def create_patch_proposal(
    plan: ImplementationPlan,
    file_reads: list[FileReadResult],
) -> PatchProposal:
    """Create a deterministic, approval-gated patch proposal.

    This layer intentionally does not edit files or create real diffs yet. It
    validates that planned files were read and preserves the original content as
    the proposed content until a later editing layer exists.
    """

    target_files = _unique_paths(plan.relevant_files)
    if not target_files:
        raise PatchProposalError(
            "Implementation plan must include at least one relevant file."
        )

    target_file_set = set(target_files)
    reads_by_path = _index_file_reads(file_reads)

    extra_reads = sorted(set(reads_by_path) - target_file_set)
    if extra_reads:
        raise PatchProposalError(
            "File reads must target only files from the implementation plan: "
            f"{', '.join(extra_reads)}"
        )

    missing_reads = [path for path in target_files if path not in reads_by_path]
    if missing_reads:
        raise PatchProposalError(
            "Missing file reads for implementation plan target files: "
            f"{', '.join(missing_reads)}"
        )

    changes = [
        _build_change_for_file(plan, reads_by_path[path])
        for path in target_files
    ]

    risks = _unique_paths(
        [
            *plan.risks,
            "Proposal preserves original content until a safe editing layer is added.",
        ]
    )

    return PatchProposal(
        summary=(
            "Prepared approval-gated patch proposal for "
            f"{len(target_files)} planned file(s)."
        ),
        target_files=target_files,
        changes=changes,
        risks=risks,
        requires_approval=True,
    )


def _unique_paths(paths: list[str]) -> list[str]:
    seen: set[str] = set()
    unique_paths: list[str] = []

    for path in paths:
        if path not in seen:
            seen.add(path)
            unique_paths.append(path)

    return unique_paths


def _index_file_reads(
    file_reads: list[FileReadResult],
) -> dict[str, FileReadResult]:
    reads_by_path: dict[str, FileReadResult] = {}

    for file_read in file_reads:
        if file_read.path in reads_by_path:
            raise PatchProposalError(f"Duplicate file read for path: {file_read.path}")
        reads_by_path[file_read.path] = file_read

    return reads_by_path


def _build_change_for_file(
    plan: ImplementationPlan,
    file_read: FileReadResult,
) -> ProposedFileChange:
    return ProposedFileChange(
        path=file_read.path,
        reason=_build_reason(plan, file_read.path),
        start_line=file_read.start_line,
        end_line=file_read.end_line,
        original_content=file_read.content,
        proposed_content=file_read.content,
    )


def _build_reason(plan: ImplementationPlan, path: str) -> str:
    matching_steps = [
        f"{step.order}. {step.description}"
        for step in plan.steps
        if path in step.target_files
    ]

    if not matching_steps:
        return "Included because the implementation plan marks this file as relevant."

    return "Planned step(s): " + " ".join(matching_steps)
