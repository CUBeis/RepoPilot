from __future__ import annotations

import json

from pydantic import ValidationError

from repopilot.llm.client import LLMClient
from repopilot.llm.models import LLMMessage, LLMRequest
from repopilot.patching.models import PatchProposal
from repopilot.planning.models import ImplementationPlan
from repopilot.tools.models import FileReadResult

DEFAULT_LLM_PATCH_PROPOSER_MODEL = "fake-patch-proposer"


class LLMPatchProposalError(ValueError):
    """Raised when an LLM-backed patch proposal cannot be created safely."""


def create_llm_patch_proposal(
    plan: ImplementationPlan,
    file_reads: list[FileReadResult],
    llm_client: LLMClient,
    *,
    model: str = DEFAULT_LLM_PATCH_PROPOSER_MODEL,
    temperature: float = 0.0,
    max_tokens: int | None = None,
) -> PatchProposal:
    """Create a patch proposal from JSON returned by an LLM client."""

    plan_paths = _unique_paths(plan.relevant_files)
    read_paths = _index_file_reads(file_reads)
    _validate_prompt_inputs(plan_paths, read_paths)

    request = _build_llm_request(
        plan=plan,
        file_reads=file_reads,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    response = llm_client.generate(request)
    proposal_data = _parse_response_json(response.content)
    proposal = _validate_proposal_schema(proposal_data)
    approved_proposal = proposal.model_copy(update={"requires_approval": True})
    _validate_proposal_targets(approved_proposal, set(plan_paths), set(read_paths))
    return approved_proposal


def _build_llm_request(
    *,
    plan: ImplementationPlan,
    file_reads: list[FileReadResult],
    model: str,
    temperature: float,
    max_tokens: int | None,
) -> LLMRequest:
    prompt = _build_patch_proposal_prompt(plan, file_reads)

    try:
        return LLMRequest(
            messages=[
                LLMMessage(
                    role="system",
                    content=(
                        "You are RepoPilot's patch proposal engine. Return only "
                        "JSON that matches the PatchProposal schema. Do not "
                        "write files or apply patches."
                    ),
                ),
                LLMMessage(role="user", content=prompt),
            ],
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    except ValidationError as error:
        raise LLMPatchProposalError(
            f"Invalid LLM request settings: {error}"
        ) from error


def _build_patch_proposal_prompt(
    plan: ImplementationPlan,
    file_reads: list[FileReadResult],
) -> str:
    plan_json = json.dumps(plan.model_dump(), indent=2)
    reads_json = json.dumps(
        [file_read.model_dump() for file_read in file_reads],
        indent=2,
    )

    return (
        "Create a patch proposal for the implementation plan below.\n"
        "Return only valid JSON with this shape:\n"
        "{\n"
        '  "summary": "short summary",\n'
        '  "target_files": ["relative/path.py"],\n'
        '  "changes": [\n'
        "    {\n"
        '      "path": "relative/path.py",\n'
        '      "reason": "why this change is proposed",\n'
        '      "start_line": 1,\n'
        '      "end_line": 3,\n'
        '      "original_content": "content from the read file",\n'
        '      "proposed_content": "replacement content"\n'
        "    }\n"
        "  ],\n"
        '  "risks": ["risk"],\n'
        '  "requires_approval": true\n'
        "}\n\n"
        "Safety rules:\n"
        "- Use only files listed in the implementation plan.\n"
        "- Propose changes only for files included in the file reads.\n"
        "- Use relative paths exactly as provided.\n"
        "- Do not include commentary outside JSON.\n\n"
        "Implementation plan:\n"
        f"{plan_json}\n\n"
        "Read-only file results:\n"
        f"{reads_json}\n"
    )


def _parse_response_json(content: str) -> object:
    try:
        return json.loads(content)
    except json.JSONDecodeError as error:
        raise LLMPatchProposalError(
            "LLM response content was not valid JSON"
        ) from error


def _validate_proposal_schema(proposal_data: object) -> PatchProposal:
    try:
        return PatchProposal.model_validate(proposal_data)
    except ValidationError as error:
        raise LLMPatchProposalError(
            "LLM response JSON did not match the PatchProposal schema"
        ) from error


def _validate_prompt_inputs(
    plan_paths: list[str],
    reads_by_path: dict[str, FileReadResult],
) -> None:
    if not plan_paths:
        raise LLMPatchProposalError(
            "Implementation plan must include at least one relevant file."
        )

    extra_reads = sorted(set(reads_by_path) - set(plan_paths))
    if extra_reads:
        raise LLMPatchProposalError(
            "File reads must target only files from the implementation plan: "
            f"{', '.join(extra_reads)}"
        )


def _validate_proposal_targets(
    proposal: PatchProposal,
    plan_paths: set[str],
    read_paths: set[str],
) -> None:
    target_paths = set(proposal.target_files)
    change_paths = {change.path for change in proposal.changes}
    proposed_paths = target_paths | change_paths

    outside_plan = sorted(proposed_paths - plan_paths)
    if outside_plan:
        raise LLMPatchProposalError(
            "LLM patch proposal referenced files outside the implementation plan: "
            f"{', '.join(outside_plan)}"
        )

    unread_paths = sorted(proposed_paths - read_paths)
    if unread_paths:
        raise LLMPatchProposalError(
            "LLM patch proposal referenced files that were not read: "
            f"{', '.join(unread_paths)}"
        )

    changes_missing_targets = sorted(change_paths - target_paths)
    if changes_missing_targets:
        raise LLMPatchProposalError(
            "LLM patch proposal changes must be listed in target_files: "
            f"{', '.join(changes_missing_targets)}"
        )


def _index_file_reads(
    file_reads: list[FileReadResult],
) -> dict[str, FileReadResult]:
    reads_by_path: dict[str, FileReadResult] = {}

    for file_read in file_reads:
        if file_read.path in reads_by_path:
            raise LLMPatchProposalError(
                f"Duplicate file read for path: {file_read.path}"
            )
        reads_by_path[file_read.path] = file_read

    return reads_by_path


def _unique_paths(paths: list[str]) -> list[str]:
    seen: set[str] = set()
    unique_paths: list[str] = []

    for path in paths:
        if path not in seen:
            seen.add(path)
            unique_paths.append(path)

    return unique_paths
