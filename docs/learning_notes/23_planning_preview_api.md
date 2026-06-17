# Learning Note 23: Planning Preview API

## What Was Built

Milestone 24 adds a safe read-only FastAPI endpoint:

```text
POST /repositories/plan-preview
```

The endpoint accepts:

```json
{
  "root_path": "D:/RepoPilot",
  "issue": "Improve repository scanner error handling",
  "top_k": 5
}
```

It returns repository context metadata plus a deterministic implementation plan
preview.

## Why A Planning Preview API Is Useful

RepoPilot already had a deterministic planning layer as a Python function. The
planning preview API makes that capability visible to clients without allowing
the system to edit files or run commands.

This is useful for:

- demos
- future frontend planning screens
- checking which files the deterministic planner thinks are relevant
- validating the scan, chunk, retrieve, and plan flow before adding real LLMs
- showing a human the intended direction before patch proposals exist

## How It Builds On Context Preview

The previous context preview endpoint exposed:

```text
scan -> chunk -> retrieve
```

This endpoint adds one more deterministic step:

```text
scan -> chunk -> retrieve -> plan
```

It delegates context creation to:

```python
build_repository_context(root_path, issue, top_k=top_k)
```

Then it delegates planning to:

```python
create_implementation_plan(issue, context)
```

The API route only validates the request, catches clear domain errors, and maps
the result into response schemas.

## Why It Uses Deterministic Planning Only

This endpoint deliberately uses the deterministic planner. That means the same
repository and issue produce the same plan every time.

Deterministic planning is useful before LLM integration because it gives the
project a stable baseline for:

- tests
- demos
- API contracts
- debugging retrieval quality
- comparing future LLM-backed plans

## Why It Does Not Call LLMs Yet

RepoPilot already has an LLM-backed planner, but this API endpoint does not use
it. Exposing real or fake LLM planning through an API raises additional design
questions:

- provider configuration
- API keys
- prompt observability
- structured output failures
- latency and cost
- user approval boundaries

This milestone avoids those concerns and keeps the endpoint predictable.

## Why Planning Is Separate From Patch Proposal

A plan says what should be inspected or changed. A patch proposal says exactly
what content should be modified.

Keeping them separate matters because:

- humans can review the plan before any proposed edits exist
- later systems can compare multiple proposal strategies for one plan
- the approval boundary remains clear
- plan previews stay safe and read-only

This endpoint does not propose patches, apply patches, write files, or run
commands.

## Safety Boundaries

The request schema validates:

- `root_path` must not be blank
- `issue` must not be blank
- `top_k` must be between 1 and 20

Scanner, context-building, and planning errors become HTTP 400 responses when
appropriate.

The response includes:

- root name
- issue
- scanned file count
- skipped file count
- total chunk count
- retrieved count
- deterministic plan fields

The response does not include:

- absolute paths
- file contents
- file hashes
- patch proposals
- validation command output
- LLM messages

## How This Prepares Future Patch Proposal Endpoints

Future endpoints can use this plan preview as the step before patch proposal
generation:

```text
scan summary API -> context preview API -> planning preview API -> patch proposal API
```

That keeps RepoPilot's API surface gradual. Each endpoint exposes one safe layer
and avoids mixing planning, editing, validation, and repair in one jump.

## Files Added Or Updated

### `src/repopilot/api/planning.py`

Defines `POST /repositories/plan-preview`.

The route builds repository context, creates a deterministic implementation
plan, and returns a typed response.

### `src/repopilot/schemas/planning.py`

Defines:

- `PlanningPreviewRequest`
- `PlanStepResponse`
- `ImplementationPlanResponse`
- `PlanningPreviewResponse`

These schemas are the API contract for planning previews.

### `src/repopilot/main.py`

Includes the planning router in the FastAPI app.

### `tests/test_planning_preview_api.py`

Tests successful plan previews, context metadata, plan fields, relative paths,
request validation, missing roots, deterministic output, omitted hashes and file
contents, and no LLM, command, patch, or write side effects.

### `README.md`

Documents the endpoint and a simple request body.

## How To Explain This In An Interview

You can explain this feature like this:

"I added a safe planning preview API that turns a repository path and issue into
a deterministic implementation plan. The endpoint first builds context using the
existing scan, chunk, and keyword retrieval pipeline, then calls the deterministic
planner and returns typed plan metadata. It does not call LLMs, propose patches,
run commands, expose file contents, or write files. This creates a safe API step
between retrieval preview and future patch proposal workflows."
