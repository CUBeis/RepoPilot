# Learning Note 29: Repair Apply API

## What Was Built

Milestone 30 adds an approval-gated FastAPI endpoint:

```text
POST /repairs/apply-approved
```

The endpoint accepts a reviewed repair `PatchProposal`, an explicit approval
flag, and an optional validation setting. It applies the repair through
RepoPilot's existing safe patch applier, or through the existing apply-and-
validate pipeline when validation is requested.

## Why Repair Application Is Separate From Repair Generation

Repair generation creates a proposed fix after a failed validation attempt.
Repair application writes that reviewed fix to disk.

Keeping those actions separate protects the human approval boundary:

- generated repairs can be inspected before they mutate files
- a caller can reject or edit a repair proposal outside RepoPilot
- repair generation can stay deterministic in tests
- file writes happen only through the safe applier

This endpoint does not create repair proposals. It only applies a proposal that
was already reviewed and approved.

## Why Approval Is Still Required

The request must include:

```json
"approved": true
```

The repair proposal must also include:

```json
"requires_approval": true
```

Both checks are delegated to the existing safe patch applier. If either check
fails, the API returns HTTP 400 and does not modify files.

## How The Endpoint Delegates To Safe Layers

When `run_validation` is `false`, the route calls:

```python
apply_patch_proposal(root_path, repair_proposal, approved=approved)
```

When `run_validation` is `true`, the route calls:

```python
apply_and_validate_patch(
    root_path,
    repair_proposal,
    approved=approved,
    validation_commands=validation_commands,
    timeout_seconds=timeout_seconds,
)
```

The API layer does not reimplement path safety, content matching, patch writes,
or command execution.

## Why Validation Is Optional

Some callers may want a narrow repair apply step. Others may want to apply a
repair and immediately run checks.

This endpoint supports both:

- `run_validation=false` applies the reviewed repair only
- `run_validation=true` applies the repair and returns validation checks

Validation commands remain allowlisted through the existing validation pipeline.
The route returns bounded stdout and stderr previews instead of full unbounded
command output.

## What The Response Omits

The response includes:

- changed file count
- relative applied file paths
- changed flags
- optional validation checks

The response intentionally omits old and new file contents. That keeps the API
focused on execution status rather than turning it into a file-content exposure
endpoint.

## Why This Does Not Call LLMs Or Self-Correct

This endpoint does not:

- call real or fake LLM clients
- generate repair proposals
- start the self-correction loop
- call failure analysis automatically
- create follow-up patches

It applies one reviewed repair proposal and optionally validates it. Any next
repair cycle must be started by another explicit workflow.

## How This Completes The Repair Approval Flow

RepoPilot now has a clear repair path:

```text
failed validation -> failure analysis -> repair approval request -> approved repair apply
```

Each step is explicit and testable. The system can prepare repairs, ask for
approval, apply approved repairs, and optionally run validation without hiding
mutation behind automatic behavior.

## Files Added Or Updated

### `src/repopilot/api/repair_apply.py`

Defines `POST /repairs/apply-approved`.

The route chooses between `apply_patch_proposal()` and
`apply_and_validate_patch()` based on `run_validation`, maps patch and command
tool errors to HTTP 400, and returns safe summaries.

### `src/repopilot/schemas/repair_apply.py`

Defines:

- `RepairApplyRequest`
- `RepairValidationResponse`
- `RepairApplyResponse`

The request validates `root_path`, `timeout_seconds`, and optional validation
command shape. The response reuses existing applied-file and validation-check
schemas.

### `src/repopilot/main.py`

Includes the repair apply router in the FastAPI app.

### `tests/test_repair_apply_api.py`

Tests direct repair application, optional validation, approval failures, content
mismatch, missing roots, relative paths, omitted old/new content, exact command
allowlisting, no LLM or repair generation side effects, no self-correction, no
failure analysis, no command execution when validation is off, no partial writes,
and deterministic output.

### `README.md`

Documents `POST /repairs/apply-approved`, a sample request body, the explicit
approval requirement, and optional validation.

## How To Explain This In An Interview

You can explain this feature like this:

"I added an approval-gated repair apply API that completes the repair approval
flow. The endpoint accepts a reviewed repair PatchProposal and explicit
approval, then delegates file mutation to the safe patch applier. If requested,
it delegates apply-and-validate behavior to the existing validation pipeline and
returns bounded command output previews. It does not generate repairs, call
LLMs, analyze failures, self-correct, or expose old/new file contents. This keeps
repair execution safe, explicit, and human-controlled."
