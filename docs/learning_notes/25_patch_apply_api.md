# Learning Note 25: Patch Apply API

## What Was Built

Milestone 26 adds RepoPilot's first mutating FastAPI endpoint:

```text
POST /patches/apply
```

The endpoint accepts:

```json
{
  "root_path": "D:/RepoPilot",
  "approved": true,
  "proposal": {
    "summary": "Update app output.",
    "target_files": ["src/app.py"],
    "changes": [
      {
        "path": "src/app.py",
        "reason": "Reviewed change.",
        "start_line": 1,
        "end_line": 1,
        "original_content": "print('old')\n",
        "proposed_content": "print('new')\n"
      }
    ],
    "risks": ["May affect app output."],
    "requires_approval": true
  }
}
```

It applies the proposal through the existing safe patch applier and returns a
small summary of changed files.

## Why This Is The First Mutating API Endpoint

Earlier API endpoints were read-only or preview-only. They could scan, retrieve,
plan, or propose, but they could not write files.

This endpoint crosses that boundary deliberately. It exists only after RepoPilot
already has:

- a structured `PatchProposal` model
- approval requirements
- path safety checks
- original-content matching
- tests for safe patch application

## Why Explicit Approval Is Required

The request must include:

```json
"approved": true
```

The proposal must also include:

```json
"requires_approval": true
```

Both checks matter. The request-level approval says the caller is authorizing
this specific apply action. The proposal-level flag says the proposal itself was
created under an approval-gated contract.

If either condition fails, the safe applier raises `PatchApplyError`, which the
API returns as HTTP 400.

## Why It Delegates To The Safe Patch Applier

The API route does not reimplement file safety. It delegates to:

```python
apply_patch_proposal(root_path, proposal, approved=approved)
```

That existing layer validates:

- repository root exists and is a directory
- paths are relative
- paths stay inside the repository
- target files exist and are not directories
- file contents are valid UTF-8
- current file content exactly matches `original_content`
- all changes validate before any file is written

Keeping those rules in one place avoids two sources of truth.

## Why It Does Not Run Validation Automatically

Patch application and validation are separate actions.

This endpoint only applies a reviewed proposal. It does not:

- run `pytest`
- run `ruff`
- call the validation pipeline
- analyze failures
- start self-correction

That separation keeps the first mutating endpoint easy to reason about. A future
endpoint can compose apply plus validation after this boundary is stable.

## Why Old And New Content Are Omitted

The safe applier returns old and new content internally because other Python
layers may need it.

The API response intentionally returns only:

- relative file path
- whether the file changed
- total changed file count

This avoids turning the apply endpoint into a file-content disclosure endpoint.

## Safety Boundaries That Remain

The endpoint still depends on local repository paths, so callers should only
allow trusted paths in real deployments.

It also does not add authentication yet. That is acceptable for this portfolio
milestone because the focus is the internal safety contract, but a production API
would need authentication, authorization, audit logging, and deployment-level
path restrictions.

## How This Prepares A Future Apply-And-Validate Endpoint

RepoPilot already has a validation pipeline:

```text
apply patch -> run validation commands
```

Now the API has the apply half exposed safely. A later endpoint can expose a
separate approval-gated apply-and-validate workflow using the existing command
allowlist.

The path becomes:

```text
patch preview API -> patch apply API -> future apply-and-validate API
```

## Files Added Or Updated

### `src/repopilot/api/apply.py`

Defines `POST /patches/apply`.

The route calls `apply_patch_proposal()` and maps `PatchApplyError` to HTTP 400.

### `src/repopilot/schemas/apply.py`

Defines:

- `PatchApplyRequest`
- `AppliedFileResponse`
- `PatchApplyResponse`

The response model omits `old_content` and `new_content`.

### `src/repopilot/main.py`

Includes the apply router in the FastAPI app.

### `tests/test_patch_apply_api.py`

Tests approved application, response shape, omitted old/new content, approval
failures, content mismatch, missing roots, relative paths, no LLM/command/
validation/self-correction calls, deterministic output, and no partial writes
when validation fails before writing.

### `README.md`

Documents `POST /patches/apply`, notes that it mutates files only when
`approved=true`, and states that validation is separate.

## How To Explain This In An Interview

You can explain this feature like this:

"I added RepoPilot's first mutating API endpoint, but kept it approval-gated and
thin. The endpoint accepts a reviewed PatchProposal and an explicit approved
flag, then delegates all path safety, content matching, and write behavior to the
existing safe patch applier. It returns only changed file summaries and does not
run tests, call LLMs, start self-correction, or expose old/new file contents.
This creates a controlled mutation boundary before adding apply-and-validate
workflows."
