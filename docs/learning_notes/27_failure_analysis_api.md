# Learning Note 27: Failure Analysis API

## What Was Built

Milestone 28 adds a safe read-only FastAPI endpoint:

```text
POST /validation/analyze-failures
```

The endpoint accepts a `PatchValidationResult` payload and returns structured
failure analysis.

## Why Failure Analysis Is Separate From Validation

Validation runs checks. Failure analysis interprets the result of those checks.

Keeping them separate matters because:

- validation can be run once and analyzed multiple ways
- analysis can be tested without executing commands
- future repair workflows can decide when to request analysis
- command execution stays isolated in the validation pipeline

This endpoint does not rerun validation. It only analyzes a supplied validation
result.

## Why This Endpoint Is Read-Only

The endpoint only receives data and returns a summary.

It does not:

- run commands
- apply patches
- read files
- write files
- call LLMs
- generate repair proposals
- start self-correction

That makes it safe to expose after apply-and-validate without adding another
mutation boundary.

## How It Turns Validation Output Into Agent-Readable Summaries

The endpoint delegates to:

```python
analyze_validation_result(validation_result, max_excerpt_chars=max_excerpt_chars)
```

The analyzer finds checks where `passed` is `False` and returns:

- check name
- command
- return code
- timeout state
- stdout excerpt
- stderr excerpt
- summary text
- whether self-correction may be needed

This turns raw command output into structured context that a future repair
planner can consume.

## Why It Does Not Repair Anything

A repair is a new patch proposal. That is a separate action with its own safety
rules and approval boundary.

This endpoint stops at analysis. It does not call an LLM, create a repair
proposal, or apply any changes.

## How It Prepares Repair Approval Workflows

Future repair workflows can follow this sequence:

```text
apply-and-validate -> analyze failures -> generate repair proposal -> request approval
```

The failure analysis API provides the middle step as a stable API contract.

## Validation Rules

The request validates:

- `validation_result` must match `PatchValidationResult`
- `max_excerpt_chars` must be between 0 and 5000

The response omits `old_content` and `new_content` from the original apply
result. It also truncates stdout and stderr excerpts to `max_excerpt_chars`.

## Files Added Or Updated

### `src/repopilot/api/analysis.py`

Defines `POST /validation/analyze-failures`.

The route calls `analyze_validation_result()` and maps the result into API
response schemas.

### `src/repopilot/schemas/analysis.py`

Defines:

- `FailureAnalysisRequest`
- `FailedCheckSummaryResponse`
- `FailureAnalysisResponse`

### `src/repopilot/main.py`

Includes the analysis router in the FastAPI app.

### `tests/test_failure_analysis_api.py`

Tests passed validation results, failed checks, timeouts, excerpt truncation,
invalid excerpt limits, omitted old/new content, no command/patch/LLM/repair/
self-correction calls, and deterministic output.

### `README.md`

Documents the endpoint, example request body, and read-only/no-repair boundary.

## How To Explain This In An Interview

You can explain this feature like this:

"I added a read-only failure analysis API that accepts a structured validation
result and returns compact failed-check summaries. It delegates to the existing
failure analyzer, bounds stdout and stderr excerpts, and omits old/new patch
contents from the response. It does not rerun commands, apply patches, call LLMs,
or generate repairs. This separates validation from interpretation and prepares
RepoPilot for future approval-gated repair workflows."
