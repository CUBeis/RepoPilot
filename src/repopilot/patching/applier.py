from __future__ import annotations

from pathlib import Path, PurePosixPath, PureWindowsPath

from repopilot.patching.models import (
    PatchAppliedFile,
    PatchApplyResult,
    PatchProposal,
    ProposedFileChange,
)


class PatchApplyError(ValueError):
    """Raised when a patch proposal cannot be applied safely."""


def apply_patch_proposal(
    root_path: str | Path,
    proposal: PatchProposal,
    *,
    approved: bool,
) -> PatchApplyResult:
    """Apply an approved patch proposal after validating every change."""

    if not approved:
        raise PatchApplyError("Patch proposal must be explicitly approved.")
    if not proposal.requires_approval:
        raise PatchApplyError("Patch proposal must require approval before applying.")

    root = _resolve_root(root_path)
    _resolve_proposal_target_paths(root=root, proposal=proposal)
    validated_changes = _validate_changes(root=root, proposal=proposal)

    applied_files: list[PatchAppliedFile] = []
    for file_path, change, current_content in validated_changes:
        changed = current_content != change.proposed_content
        if changed:
            _write_utf8_content(file_path=file_path, content=change.proposed_content)

        applied_files.append(
            PatchAppliedFile(
                path=_relative_posix_path(root=root, file_path=file_path),
                old_content=current_content,
                new_content=change.proposed_content,
                changed=changed,
            )
        )

    return PatchApplyResult(
        applied_files=applied_files,
        changed_file_count=sum(
            1 for applied_file in applied_files if applied_file.changed
        ),
    )


def _resolve_root(root_path: str | Path) -> Path:
    root = Path(root_path).expanduser()
    if not root.exists():
        raise PatchApplyError(f"Repository root does not exist: {root}")
    if not root.is_dir():
        raise PatchApplyError(f"Repository root is not a directory: {root}")
    return root.resolve()


def _resolve_proposal_target_paths(*, root: Path, proposal: PatchProposal) -> None:
    for path in proposal.target_files:
        _resolve_relative_file(root=root, relative_path=path)


def _validate_changes(
    *,
    root: Path,
    proposal: PatchProposal,
) -> list[tuple[Path, ProposedFileChange, str]]:
    target_files = set(proposal.target_files)
    seen_change_paths: set[str] = set()
    validated_changes: list[tuple[Path, ProposedFileChange, str]] = []

    for change in proposal.changes:
        if change.path not in target_files:
            raise PatchApplyError(
                f"Patch change path is not listed in target_files: {change.path}"
            )
        if change.path in seen_change_paths:
            raise PatchApplyError(f"Duplicate patch change for path: {change.path}")
        seen_change_paths.add(change.path)

        file_path = _resolve_relative_file(root=root, relative_path=change.path)
        current_content = _read_utf8_content(file_path=file_path)
        if current_content != change.original_content:
            raise PatchApplyError(
                "Current file content does not match proposal original_content: "
                f"{change.path}"
            )
        validated_changes.append((file_path, change, current_content))

    return validated_changes


def _resolve_relative_file(*, root: Path, relative_path: str) -> Path:
    if not relative_path.strip():
        raise PatchApplyError("Patch path must not be empty")
    if _is_absolute_path(relative_path):
        raise PatchApplyError(f"Patch path must be relative: {relative_path}")

    file_path = (root / relative_path).resolve()
    try:
        file_path.relative_to(root)
    except ValueError as error:
        raise PatchApplyError(
            f"Patch path escapes repository root: {relative_path}"
        ) from error

    if not file_path.exists():
        raise PatchApplyError(f"Patch target file does not exist: {relative_path}")
    if file_path.is_dir():
        raise PatchApplyError(
            f"Patch target path is a directory, not a file: {relative_path}"
        )
    if not file_path.is_file():
        raise PatchApplyError(f"Patch target is not a regular file: {relative_path}")

    return file_path


def _is_absolute_path(path: str) -> bool:
    return (
        Path(path).is_absolute()
        or PureWindowsPath(path).is_absolute()
        or PurePosixPath(path).is_absolute()
        or path.startswith(("/", "\\"))
    )


def _read_utf8_content(*, file_path: Path) -> str:
    try:
        content_bytes = file_path.read_bytes()
    except OSError as error:
        raise PatchApplyError(
            f"Could not read patch target file: {file_path}"
        ) from error

    if b"\x00" in content_bytes:
        raise PatchApplyError(f"Patch target appears to be binary: {file_path}")

    try:
        return content_bytes.decode("utf-8")
    except UnicodeDecodeError as error:
        raise PatchApplyError(
            f"Patch target file is not valid UTF-8: {file_path}"
        ) from error


def _write_utf8_content(*, file_path: Path, content: str) -> None:
    try:
        file_path.write_bytes(content.encode("utf-8"))
    except OSError as error:
        raise PatchApplyError(
            f"Could not write patch target file: {file_path}"
        ) from error


def _relative_posix_path(*, root: Path, file_path: Path) -> str:
    return file_path.relative_to(root).as_posix()
