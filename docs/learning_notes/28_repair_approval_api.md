# Learning Note 28: Repair Approval API

## What Was Built

Milestone 29 adds a safe FastAPI endpoint:

```text
POST /repairs/approval-request
```

The endpoint accepts a failed `SelfCorrectionAttempt`, read-only file context,
and fake LLM response JSON. It returns a `RepairApprovalRequest`-style response
containing a generated repair proposal that still requires human approval.

## Why Repair Approval Is Separate From Failure Analysis

Failure analysis explains what went wrong. Repair approval prepares a proposed
fix for review.

Keeping them separate matters because:

- a failed validation result can be analyzed without generating a patch
- repair generation can be reviewed before any file mutation
- different repair strategies can consume the same failure analysis later
- the approval boundary stays visible and testable

This endpoint assumes failure analysis already exists inside the failed attempt.

## Why This Endpoint Uses `FakeLLMClient`

The project already has a provider-independent `LLMClient` abstraction, but this
API milestone does not configure real providers.

Instead, callers provide:

```json
"llm_response_json": "{...}"
```

The route wraps that string in `FakeLLMClient` and passes it to the existing
repair workflow. This keeps the API deterministic, testable, and free of API
keys or network calls.

## Why Generated Repairs Still Require Approval

Even when a repair proposal is valid JSON and targets the right files, it is
still generated content.

The workflow forces:

```json
"approval_required": true
"repair_proposal.requires_approval": true
```

That means a future caller must explicitly approve the repair before any apply
endpoint can write it to disk.

## Why It Does Not Apply Patches Or Run Validation

This endpoint only prepares a repair approval request.

It does not:

- apply patches
- run validation commands
- run shell commands
- read files from disk
- write files
- start self-correction
- call real LLM providers

The repair proposal is returned for review, not execution.

## How It Protects The Approval Boundary

The endpoint delegates to:

```python
prepare_repair_for_approval(failed_attempt, file_reads, llm_client)
```

That workflow uses the existing LLM repair proposal generator, which validates:

- the attempt actually failed
- failure analysis indicates self-correction is needed
- proposed files were part of the failed attempt
- proposed files were included in supplied read-only file context
- the fake LLM response matches the `PatchProposal` schema

Invalid JSON, invalid proposal shape, passed attempts, outside files, and unread
files become HTTP 400 responses.

## How This Prepares Future Real-Provider Repair Workflows

Later, RepoPilot can replace the fake response string with a real provider-backed
`LLMClient`.

The workflow boundary will stay the same:

```text
failed attempt + failure analysis + file reads + LLMClient -> repair proposal -> approval request
```

That makes this milestone a safe API contract before adding provider
configuration, secrets, retries, logging, or cost controls.

## Files Added Or Updated

### `src/repopilot/api/repairs.py`

Defines `POST /repairs/approval-request`.

The route creates a `FakeLLMClient` from `llm_response_json`, calls
`prepare_repair_for_approval()`, maps `LLMRepairProposalError` to HTTP 400, and
returns a response with approval required.

### `src/repopilot/schemas/repairs.py`

Defines:

- `RepairApprovalApiRequest`
- `ProposedFileChangeApiResponse`
- `PatchProposalApiResponse`
- `RepairApprovalApiResponse`

### `src/repopilot/main.py`

Includes the repair router in the FastAPI app.

### `tests/test_repair_approval_api.py`

Tests valid approval requests, approval forcing, failed attempt numbers,
invalid JSON, invalid proposal schemas, passed attempts, outside target files,
unread target files, request validation, model settings, no mutation or command
side effects, fake client usage, and deterministic output.

### `README.md`

Documents the endpoint, example payload, fake LLM JSON behavior, and the fact
that it returns an approval request without mutating files.

## How To Explain This In An Interview

You can explain this feature like this:

"I added a repair approval API that turns a failed validation attempt, failure
analysis, read-only file context, and deterministic fake LLM response into a
repair proposal awaiting human approval. The endpoint delegates to the existing
repair workflow, forces approval to remain required, and validates that proposed
files were both part of the failed attempt and included in supplied file reads.
It does not apply patches, run commands, call real providers, read from disk, or
start self-correction. This creates the API contract for future real-provider
repair generation while preserving the approval boundary."
