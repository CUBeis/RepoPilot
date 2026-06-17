# 11 - Safe Patch Applier

Milestone 12 adds the first write-capable layer in RepoPilot: a safe patch
applier. It accepts a repository root, a `PatchProposal`, and an explicit
approval flag. If every safety check passes, it writes proposed UTF-8 content to
disk and returns a structured `PatchApplyResult`.

This milestone does not run tests, execute shell commands, call LLMs, add API
endpoints, or self-correct from failures.

## What Was Built

The main function is:

```python
apply_patch_proposal(
    root_path,
    proposal,
    approved=True,
)
```

It returns:

- `PatchApplyResult`
- `PatchAppliedFile` records for each proposed change
- `changed_file_count`

Each applied file record includes:

- Relative path
- Old content
- New content
- Whether the file changed

## Why Approval Is Required

Patch application writes to disk. That makes it much riskier than scanning,
retrieval, planning, reading, or proposing.

The applier refuses to run unless:

- The caller passes `approved=True`.
- The proposal has `requires_approval=True`.

This keeps human-in-the-loop control explicit. A future agent should not be able
to silently bypass approval by returning a proposal that says approval is not
needed.

## Why Original Content Matching Matters

Before writing, the applier reads the current file content and compares it to
`change.original_content`.

If the content does not match exactly, the applier refuses to write anything.

This protects against stale proposals. For example, a file may have changed
after RepoPilot read it but before the proposal was applied. Exact matching
prevents RepoPilot from overwriting newer work with an old edit.

## All-Or-Nothing Validation

The applier validates every proposed change before writing any file.

It checks:

- The repository root exists and is a directory.
- Paths are relative.
- Paths stay inside the repository root.
- Files exist.
- Targets are not directories.
- Files are valid UTF-8 text.
- Current file content matches `original_content`.
- Each change path is listed in `target_files`.
- Duplicate change paths are rejected.

Only after all checks pass does it write `proposed_content`.

## Why This Still Does Not Run Tests Or Self-Correct

Applying a patch is not the same as validating a patch.

This milestone writes approved content safely, but it does not:

- Run pytest
- Run Ruff
- Execute shell commands
- Inspect failures
- Ask an LLM to repair code
- Loop until checks pass

Those are separate agent abilities that need their own safety boundaries and
tests.

## How This Fits The Workflow

The RepoPilot workflow now looks like:

```text
scan -> chunk -> retrieve -> plan -> read files -> propose patch -> approve -> apply
```

The next layers can add diff previews, test execution, self-correction, and
PR-ready summaries.

## Files Involved

### `src/repopilot/patching/models.py`

Adds `PatchAppliedFile` and `PatchApplyResult`.

What to learn:

- Write operations should return structured results, not loose text.
- A result should say which files were touched and whether content changed.

### `src/repopilot/patching/applier.py`

Implements `apply_patch_proposal()` and `PatchApplyError`.

What to learn:

- File writes should be protected by path safety, approval checks, and stale
  content checks.
- Validation should happen before mutation.
- UTF-8 handling should stay explicit.

### `tests/test_patch_applier.py`

Tests approval refusal, approved application, unchanged no-op behavior, path
safety, missing files, directories, content mismatch, deterministic multi-file
application, and no partial writes.

What to learn:

- Write-capable code needs strong negative tests.
- Safety tests should prove that failed validation leaves files unchanged.

## Interview Explanation

You can explain this feature like this:

"I added RepoPilot's first safe write layer. The patch applier accepts a
PatchProposal and applies it only when explicit approval is provided. It rejects
unsafe paths, missing files, directories, stale content, duplicate changes, and
unapproved proposals. It validates every change before writing anything, then
writes UTF-8 proposed content and returns a structured result. It still does not
run tests or self-correct; those are separate future agent capabilities."
