from pathlib import Path

import pytest

from repopilot.patching import (
    PatchApplyError,
    PatchProposal,
    ProposedFileChange,
    apply_patch_proposal,
)


def test_refuses_without_approval(tmp_path: Path) -> None:
    _write_file(tmp_path, "src/auth.py", "old\n")

    with pytest.raises(PatchApplyError, match="explicitly approved"):
        apply_patch_proposal(tmp_path, _make_proposal(), approved=False)


def test_refuses_if_proposal_requires_approval_is_false(tmp_path: Path) -> None:
    _write_file(tmp_path, "src/auth.py", "old\n")
    proposal = _make_proposal(requires_approval=False)

    with pytest.raises(PatchApplyError, match="must require approval"):
        apply_patch_proposal(tmp_path, proposal, approved=True)


def test_applies_approved_proposal(tmp_path: Path) -> None:
    target_file = _write_file(tmp_path, "src/auth.py", "old\n")

    result = apply_patch_proposal(tmp_path, _make_proposal(), approved=True)

    assert target_file.read_text(encoding="utf-8") == "new\n"
    assert result.applied_files[0].path == "src/auth.py"
    assert result.applied_files[0].old_content == "old\n"
    assert result.applied_files[0].new_content == "new\n"
    assert result.applied_files[0].changed is True


def test_returns_changed_file_count(tmp_path: Path) -> None:
    _write_file(tmp_path, "src/auth.py", "old\n")

    result = apply_patch_proposal(tmp_path, _make_proposal(), approved=True)

    assert result.changed_file_count == 1


def test_skips_unchanged_content_safely(tmp_path: Path) -> None:
    target_file = _write_file(tmp_path, "src/auth.py", "same\n")
    proposal = _make_proposal(original_content="same\n", proposed_content="same\n")

    result = apply_patch_proposal(tmp_path, proposal, approved=True)

    assert target_file.read_text(encoding="utf-8") == "same\n"
    assert result.applied_files[0].changed is False
    assert result.changed_file_count == 0


def test_rejects_path_traversal(tmp_path: Path) -> None:
    proposal = _make_proposal(path="../secret.txt")

    with pytest.raises(PatchApplyError, match="escapes repository root"):
        apply_patch_proposal(tmp_path, proposal, approved=True)


def test_rejects_absolute_paths(tmp_path: Path) -> None:
    absolute_path = str(tmp_path / "src" / "auth.py")
    proposal = _make_proposal(path=absolute_path)

    with pytest.raises(PatchApplyError, match="must be relative"):
        apply_patch_proposal(tmp_path, proposal, approved=True)


def test_rejects_missing_files(tmp_path: Path) -> None:
    with pytest.raises(PatchApplyError, match="does not exist"):
        apply_patch_proposal(tmp_path, _make_proposal(), approved=True)


def test_rejects_directories(tmp_path: Path) -> None:
    (tmp_path / "src" / "auth.py").mkdir(parents=True)

    with pytest.raises(PatchApplyError, match="directory"):
        apply_patch_proposal(tmp_path, _make_proposal(), approved=True)


def test_rejects_content_mismatch(tmp_path: Path) -> None:
    _write_file(tmp_path, "src/auth.py", "current\n")

    with pytest.raises(PatchApplyError, match="does not match"):
        apply_patch_proposal(tmp_path, _make_proposal(), approved=True)


def test_applies_multiple_files_deterministically(tmp_path: Path) -> None:
    first_file = _write_file(tmp_path, "src/routes.py", "route old\n")
    second_file = _write_file(tmp_path, "src/auth.py", "auth old\n")
    proposal = PatchProposal(
        summary="Update two files.",
        target_files=["src/routes.py", "src/auth.py"],
        changes=[
            _make_change(
                path="src/routes.py",
                original_content="route old\n",
                proposed_content="route new\n",
            ),
            _make_change(
                path="src/auth.py",
                original_content="auth old\n",
                proposed_content="auth new\n",
            ),
        ],
        risks=[],
        requires_approval=True,
    )

    result = apply_patch_proposal(tmp_path, proposal, approved=True)

    assert [applied_file.path for applied_file in result.applied_files] == [
        "src/routes.py",
        "src/auth.py",
    ]
    assert first_file.read_text(encoding="utf-8") == "route new\n"
    assert second_file.read_text(encoding="utf-8") == "auth new\n"
    assert result.changed_file_count == 2


def test_writes_nothing_when_validation_fails_before_applying(
    tmp_path: Path,
) -> None:
    first_file = _write_file(tmp_path, "src/auth.py", "auth old\n")
    second_file = _write_file(tmp_path, "src/routes.py", "route current\n")
    proposal = PatchProposal(
        summary="Update two files.",
        target_files=["src/auth.py", "src/routes.py"],
        changes=[
            _make_change(
                path="src/auth.py",
                original_content="auth old\n",
                proposed_content="auth new\n",
            ),
            _make_change(
                path="src/routes.py",
                original_content="route old\n",
                proposed_content="route new\n",
            ),
        ],
        risks=[],
        requires_approval=True,
    )

    with pytest.raises(PatchApplyError, match="does not match"):
        apply_patch_proposal(tmp_path, proposal, approved=True)

    assert first_file.read_text(encoding="utf-8") == "auth old\n"
    assert second_file.read_text(encoding="utf-8") == "route current\n"


def _make_proposal(
    *,
    path: str = "src/auth.py",
    original_content: str = "old\n",
    proposed_content: str = "new\n",
    requires_approval: bool = True,
) -> PatchProposal:
    return PatchProposal(
        summary="Update auth file.",
        target_files=[path],
        changes=[
            _make_change(
                path=path,
                original_content=original_content,
                proposed_content=proposed_content,
            )
        ],
        risks=[],
        requires_approval=requires_approval,
    )


def _make_change(
    *,
    path: str,
    original_content: str,
    proposed_content: str,
) -> ProposedFileChange:
    return ProposedFileChange(
        path=path,
        reason="Apply requested update.",
        start_line=1,
        end_line=1,
        original_content=original_content,
        proposed_content=proposed_content,
    )


def _write_file(root: Path, relative_path: str, content: str) -> Path:
    file_path = root / relative_path
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_bytes(content.encode("utf-8"))
    return file_path
