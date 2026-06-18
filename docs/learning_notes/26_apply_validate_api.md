# Learning Note 26: Apply-And-Validate API

## What Was Built

Milestone 27 adds an approval-gated FastAPI endpoint:

```text
POST /patches/apply-and-validate
```

The endpoint accepts a reviewed `PatchProposal`, an explicit approval flag, and
optional validation commands. It applies the patch through RepoPilot's safe patch
applier and then runs allowlisted validation commands through the existing
validation pipeline.

## Why Apply-And-Validate Is Separate From Apply-Only

Milestone 26 introduced the apply-only endpoint. That endpoint writes an
approved patch and stops.

Apply-and-validate is a larger workflow:

```text
apply patch -> run validation commands -> return structured validation result
```

Keeping it separate matters because some callers may want to apply only, while
others may want immediate checks. It also keeps each API endpoint easier to
reason about and test.

## Why Validation Commands Are Allowlisted

Validation commands can execute programs, so they need a strict safety boundary.

RepoPilot's safe command runner only runs commands that exactly match an
allowlist. This endpoint passes the requested `validation_commands` into the
validation pipeline, and the pipeline uses those exact commands as the command
allowlist.

If no commands are provided, the existing validation pipeline defaults are used:

```python
["pytest"]
["ruff", "check", "."]
```

The endpoint does not accept shell strings and does not use `shell=True`.

## Why Stdout And Stderr Are Bounded

Validation output can be large. Test failures, linters, or traceback-heavy
commands can produce thousands of characters.

The API response returns:

- `stdout_preview`
- `stderr_preview`

Each is truncated internally to 2000 characters. That keeps API responses
useful without exposing unbounded command output.

## Why This Endpoint Still Does Not Self-Correct

A failed validation result is information. Self-correction is a separate action.

This endpoint does not:

- analyze failures
- generate repair proposals
- call LLMs
- start the self-correction loop
- apply any repair

It only applies the reviewed proposal and reports whether validation passed.

## Why Failure Analysis Remains Separate

RepoPilot already has a failure analyzer that turns failed validation checks
into structured summaries. This endpoint does not call it automatically.

Keeping failure analysis separate is useful because:

- callers can decide when they want analysis
- validation remains a simple apply-and-check workflow
- future repair endpoints can explicitly consume failure analysis
- the API response remains focused on command results

## Safety Boundaries That Remain

This endpoint mutates files, so it still requires trusted deployment boundaries.
A production version should add authentication, authorization, audit logs, and
repository path restrictions.

Within the current project, safety comes from:

- explicit `approved=true`
- `proposal.requires_approval=true`
- safe patch applier path checks
- exact `original_content` matching
- all changes validated before writes
- command allowlisting
- bounded command output previews

## How This Prepares Future Failure-Analysis And Repair Endpoints

The endpoint returns structured validation checks. A future endpoint can take
those checks and run:

```text
validation result -> failure analysis -> repair proposal -> approval request
```

That keeps each stage explicit instead of hiding the whole loop behind one
automatic endpoint.

## Files Added Or Updated

### `src/repopilot/api/validation.py`

Defines `POST /patches/apply-and-validate`.

The route delegates to `apply_and_validate_patch()` and maps patch/command
safety errors to HTTP 400.

### `src/repopilot/schemas/validation.py`

Defines:

- `ApplyAndValidateRequest`
- `ValidationCheckResponse`
- `ApplyAndValidateResponse`

The response uses bounded stdout/stderr previews and reuses
`AppliedFileResponse`.

### `src/repopilot/main.py`

Includes the validation router in the FastAPI app.

### `tests/test_apply_validate_api.py`

Tests successful apply-and-validate calls, failed commands, bounded output,
approval failures, content mismatch, missing roots, invalid timeouts, invalid
commands, HTTP 400 mapping for command-tool errors, exact allowlist forwarding,
no LLM/repair/self-correction/failure-analysis calls, relative paths, and no
partial writes on failed apply.

### `README.md`

Documents the endpoint, example request body, approval requirement, command
allowlisting, and the fact that validation remains distinct from repair.

## How To Explain This In An Interview

You can explain this feature like this:

"I added an approval-gated apply-and-validate API that composes RepoPilot's safe
patch applier and safe command runner through the existing validation pipeline.
The endpoint applies a reviewed PatchProposal only after explicit approval, then
runs exact allowlisted validation commands and returns bounded stdout/stderr
previews. It does not call LLMs, analyze failures, generate repairs, or start
self-correction. That keeps validation observable while preserving clear safety
and workflow boundaries."
