from __future__ import annotations

import json

from pydantic import ValidationError

from repopilot.agent.models import SelfCorrectionAttempt
from repopilot.llm.client import LLMClient
from repopilot.llm.models import LLMMessage, LLMRequest
from repopilot.patching.models import PatchProposal
from repopilot.tools.models import FileReadResult

DEFAULT_LLM_REPAIR_PROPOSER_MODEL = "fake-repair-proposer"


class LLMRepairProposalError(ValueError):
    """Raised when an LLM-backed repair proposal cannot be created safely."""


def create_llm_repair_proposal(
    failed_attempt: SelfCorrectionAttempt,
    file_reads: list[FileReadResult],
    llm_client: LLMClient,
    *,
    model: str = DEFAULT_LLM_REPAIR_PROPOSER_MODEL,
    temperature: float = 0.0,
    max_tokens: int | None = None,
) -> PatchProposal:
    """Create a repair proposal from a failed attempt and read-only context."""

    _validate_failed_attempt(failed_attempt)
    attempt_paths = _attempt_target_paths(failed_attempt)
    reads_by_path = _index_file_reads(file_reads)
    _validate_prompt_inputs(attempt_paths)

    request = _build_llm_request(
        failed_attempt=failed_attempt,
        file_reads=file_reads,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    response = llm_client.generate(request)
    proposal_data = _parse_response_json(response.content)
    proposal = _validate_proposal_schema(proposal_data)
    approved_proposal = proposal.model_copy(update={"requires_approval": True})
    _validate_proposal_targets(
        approved_proposal,
        set(attempt_paths),
        set(reads_by_path),
    )
    return approved_proposal


def _build_llm_request(
    *,
    failed_attempt: SelfCorrectionAttempt,
    file_reads: list[FileReadResult],
    model: str,
    temperature: float,
    max_tokens: int | None,
) -> LLMRequest:
    prompt = _build_repair_prompt(failed_attempt, file_reads)

    try:
        return LLMRequest(
            messages=[
                LLMMessage(
                    role="system",
                    content=(
                        "You are RepoPilot's repair proposal engine. Return "
                        "only JSON that matches the PatchProposal schema. Do "
                        "not write files, apply patches, or run commands."
                    ),
                ),
                LLMMessage(role="user", content=prompt),
            ],
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    except ValidationError as error:
        raise LLMRepairProposalError(
            f"Invalid LLM request settings: {error}"
        ) from error


def _build_repair_prompt(
    failed_attempt: SelfCorrectionAttempt,
    file_reads: list[FileReadResult],
) -> str:
    attempt_json = json.dumps(failed_attempt.model_dump(), indent=2)
    reads_json = json.dumps(
        [file_read.model_dump() for file_read in file_reads],
        indent=2,
    )

    return (
        "Create a repair patch proposal for the failed validation attempt "
        "below.\n"
        "Return only valid JSON with this shape:\n"
        "{\n"
        '  "summary": "short repair summary",\n'
        '  "target_files": ["relative/path.py"],\n'
        '  "changes": [\n'
        "    {\n"
        '      "path": "relative/path.py",\n'
        '      "reason": "why this repair is proposed",\n'
        '      "start_line": 1,\n'
        '      "end_line": 3,\n'
        '      "original_content": "current content from the read file",\n'
        '      "proposed_content": "replacement content"\n'
        "    }\n"
        "  ],\n"
        '  "risks": ["risk"],\n'
        '  "requires_approval": true\n'
        "}\n\n"
        "Safety rules:\n"
        "- Use only files targeted by the failed attempt.\n"
        "- Propose changes only for files included in the file reads.\n"
        "- Use relative paths exactly as provided.\n"
        "- Address the validation failure analysis directly.\n"
        "- Do not include commentary outside JSON.\n\n"
        "Failed attempt:\n"
        f"{attempt_json}\n\n"
        "Read-only file results:\n"
        f"{reads_json}\n"
    )


def _validate_failed_attempt(failed_attempt: SelfCorrectionAttempt) -> None:
    if failed_attempt.validation_result.passed:
        raise LLMRepairProposalError(
            "Repair proposals require a failed validation attempt."
        )

    if failed_attempt.failure_analysis.passed:
        raise LLMRepairProposalError(
            "Repair proposals require failure analysis for a failed attempt."
        )

    if not failed_attempt.failure_analysis.needs_self_correction:
        raise LLMRepairProposalError(
            "Failure analysis must indicate that self-correction is needed."
        )


def _parse_response_json(content: str) -> object:
    try:
        return json.loads(content)
    except json.JSONDecodeError as error:
        raise LLMRepairProposalError(
            "LLM response content was not valid JSON"
        ) from error


def _validate_proposal_schema(proposal_data: object) -> PatchProposal:
    try:
        return PatchProposal.model_validate(proposal_data)
    except ValidationError as error:
        raise LLMRepairProposalError(
            "LLM response JSON did not match the PatchProposal schema"
        ) from error


def _validate_prompt_inputs(
    attempt_paths: list[str],
) -> None:
    if not attempt_paths:
        raise LLMRepairProposalError(
            "Failed attempt must include at least one target file."
        )


def _validate_proposal_targets(
    proposal: PatchProposal,
    attempt_paths: set[str],
    read_paths: set[str],
) -> None:
    target_paths = set(proposal.target_files)
    change_paths = {change.path for change in proposal.changes}
    proposed_paths = target_paths | change_paths

    outside_attempt = sorted(proposed_paths - attempt_paths)
    if outside_attempt:
        raise LLMRepairProposalError(
            "LLM repair proposal referenced files outside the failed attempt: "
            f"{', '.join(outside_attempt)}"
        )

    unread_paths = sorted(proposed_paths - read_paths)
    if unread_paths:
        raise LLMRepairProposalError(
            "LLM repair proposal referenced files that were not read: "
            f"{', '.join(unread_paths)}"
        )

    changes_missing_targets = sorted(change_paths - target_paths)
    if changes_missing_targets:
        raise LLMRepairProposalError(
            "LLM repair proposal changes must be listed in target_files: "
            f"{', '.join(changes_missing_targets)}"
        )


def _index_file_reads(
    file_reads: list[FileReadResult],
) -> dict[str, FileReadResult]:
    reads_by_path: dict[str, FileReadResult] = {}

    for file_read in file_reads:
        if file_read.path in reads_by_path:
            raise LLMRepairProposalError(
                f"Duplicate file read for path: {file_read.path}"
            )
        reads_by_path[file_read.path] = file_read

    return reads_by_path


def _attempt_target_paths(failed_attempt: SelfCorrectionAttempt) -> list[str]:
    paths = [
        *failed_attempt.proposal.target_files,
        *(change.path for change in failed_attempt.proposal.changes),
    ]
    return _unique_paths(paths)


def _unique_paths(paths: list[str]) -> list[str]:
    seen: set[str] = set()
    unique_paths: list[str] = []

    for path in paths:
        if path not in seen:
            seen.add(path)
            unique_paths.append(path)

    return unique_paths
