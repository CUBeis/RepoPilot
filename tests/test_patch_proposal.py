from pathlib import Path

import pytest

from repopilot.patching import (
    PatchProposalError,
    create_patch_proposal,
)
from repopilot.planning import ImplementationPlan, PlanStep
from repopilot.tools import FileReadResult, read_text_file


def test_creates_patch_proposal_from_plan_and_file_reads() -> None:
    plan = _make_plan(["src/auth.py"])
    file_read = _make_file_read("src/auth.py", "def login():\n    return True\n")

    proposal = create_patch_proposal(plan, [file_read])

    expected_summary = "Prepared approval-gated patch proposal for 1 planned file(s)."
    assert proposal.summary == expected_summary
    assert proposal.target_files == ["src/auth.py"]
    assert len(proposal.changes) == 1
    assert proposal.changes[0].path == "src/auth.py"
    assert proposal.changes[0].reason == "Planned step(s): 1. Inspect src/auth.py."


def test_requires_approval_by_default() -> None:
    proposal = create_patch_proposal(
        _make_plan(["src/auth.py"]),
        [_make_file_read("src/auth.py", "content\n")],
    )

    assert proposal.requires_approval is True


def test_preserves_original_content() -> None:
    content = "line one\nline two\n"
    proposal = create_patch_proposal(
        _make_plan(["src/auth.py"]),
        [_make_file_read("src/auth.py", content)],
    )

    change = proposal.changes[0]
    assert change.original_content == content
    assert change.proposed_content == content


def test_creates_changes_for_read_target_files_in_plan_order() -> None:
    plan = _make_plan(["src/auth.py", "src/routes.py"])
    reads = [
        _make_file_read("src/routes.py", "route\n"),
        _make_file_read("src/auth.py", "auth\n"),
    ]

    proposal = create_patch_proposal(plan, reads)

    assert proposal.target_files == ["src/auth.py", "src/routes.py"]
    assert [change.path for change in proposal.changes] == [
        "src/auth.py",
        "src/routes.py",
    ]


def test_produces_deterministic_output() -> None:
    plan = _make_plan(["src/auth.py"])
    reads = [_make_file_read("src/auth.py", "content\n")]

    first = create_patch_proposal(plan, reads)
    second = create_patch_proposal(plan, reads)

    assert first.model_dump() == second.model_dump()


def test_rejects_plans_with_no_relevant_files() -> None:
    plan = _make_plan([])

    with pytest.raises(PatchProposalError, match="at least one relevant file"):
        create_patch_proposal(plan, [])


def test_rejects_missing_file_reads_for_target_files() -> None:
    plan = _make_plan(["src/auth.py", "src/routes.py"])
    reads = [_make_file_read("src/auth.py", "auth\n")]

    with pytest.raises(PatchProposalError, match="Missing file reads"):
        create_patch_proposal(plan, reads)


def test_rejects_file_reads_not_in_plan_target_files() -> None:
    plan = _make_plan(["src/auth.py"])
    reads = [
        _make_file_read("src/auth.py", "auth\n"),
        _make_file_read("src/extra.py", "extra\n"),
    ]

    with pytest.raises(PatchProposalError, match="target only files"):
        create_patch_proposal(plan, reads)


def test_rejects_duplicate_file_reads() -> None:
    plan = _make_plan(["src/auth.py"])
    reads = [
        _make_file_read("src/auth.py", "first\n"),
        _make_file_read("src/auth.py", "second\n"),
    ]

    with pytest.raises(PatchProposalError, match="Duplicate file read"):
        create_patch_proposal(plan, reads)


def test_does_not_write_to_disk(tmp_path: Path) -> None:
    source_file = tmp_path / "src" / "auth.py"
    source_file.parent.mkdir()
    source_file.write_text("def login():\n    return True\n", encoding="utf-8")

    file_read = read_text_file(tmp_path, "src/auth.py")
    create_patch_proposal(_make_plan(["src/auth.py"]), [file_read])

    assert source_file.read_text(encoding="utf-8") == "def login():\n    return True\n"


def _make_plan(relevant_files: list[str]) -> ImplementationPlan:
    return ImplementationPlan(
        objective="Fix login behavior",
        relevant_files=relevant_files,
        steps=[
            PlanStep(
                order=index,
                description=f"Inspect {path}.",
                target_files=[path],
            )
            for index, path in enumerate(relevant_files, start=1)
        ],
        risks=["May affect authentication flow."],
        assumptions=["Read-only context is available."],
        confidence=0.8 if relevant_files else 0.2,
    )


def _make_file_read(path: str, content: str) -> FileReadResult:
    total_lines = len(content.splitlines())
    return FileReadResult(
        path=path,
        start_line=1 if content else 0,
        end_line=total_lines,
        content=content,
        total_lines=total_lines,
        size_bytes=len(content.encode("utf-8")),
    )
