# Learning Note 24: Patch Preview API

## What Was Built

Milestone 25 adds a safe FastAPI endpoint:

```text
POST /repositories/patch-preview
```

The endpoint accepts:

```json
{
  "root_path": "D:/RepoPilot",
  "issue": "Improve repository scanner error handling",
  "top_k": 5,
  "max_preview_chars": 500
}
```

It returns repository context metadata, a deterministic implementation plan, and
a bounded preview of a deterministic approval-gated patch proposal.

## Why A Patch Preview API Is Useful

RepoPilot already had a deterministic patch proposal layer. This endpoint makes
that layer visible through the API without giving the API permission to write
files.

It helps a user or future UI answer:

- What files would RepoPilot target?
- Why would each file be included?
- What content range would be proposed?
- Would approval be required before application?

The answer is a preview, not an edit.

## How It Builds On Planning Preview

The planning preview endpoint exposed:

```text
scan -> chunk -> retrieve -> plan
```

Patch preview adds safe file reads and deterministic proposal creation:

```text
scan -> chunk -> retrieve -> plan -> read planned files -> propose
```

The route delegates to existing layers:

```python
build_repository_context(root_path, issue, top_k=top_k)
create_implementation_plan(issue, context)
read_text_file(root_path, path)
create_patch_proposal(plan, file_reads)
```

The API layer only validates input, maps domain errors to HTTP 400, and returns a
bounded response.

## Why It Reads Files Only Through Safe Read-Only Tools

Patch proposals need original file content. Instead of reading arbitrary paths
directly, the endpoint uses `read_text_file()`.

That tool already handles safety rules:

- relative paths only
- no path traversal
- repository root validation
- UTF-8 text only
- size and line limits
- structured metadata

Using the tool keeps filesystem safety centralized.

## Why It Returns Bounded Previews

`PatchProposal` stores full `original_content` and `proposed_content` internally.
The API response intentionally exposes only:

- `original_preview`
- `proposed_preview`

Each preview is truncated to `max_preview_chars`.

The request schema limits that value:

```text
50 <= max_preview_chars <= 2000
```

This prevents the endpoint from becoming an unbounded file-content API.

## Why Proposal Creation Is Separate From Patch Application

A patch proposal describes what could change. Patch application writes the
change to disk.

Keeping those steps separate matters because:

- users can review the proposal first
- approval remains explicit
- API callers cannot mutate repositories through this preview endpoint
- validation and self-correction remain separate later workflow steps

## Why Approval Is Still Required

The deterministic patch proposal layer marks proposals as approval-gated. The
API response keeps `requires_approval=True`.

That makes the human approval checkpoint visible even though this endpoint does
not apply anything.

## Why This Endpoint Does Not Call LLMs Or Mutate Files

The endpoint does not:

- call LLM clients
- use `create_llm_patch_proposal()`
- apply patches
- run validation commands
- run shell commands
- write files

It only composes deterministic and read-only layers.

## How This Prepares Future Approval And Apply Endpoints

Future endpoints can use this preview as the review step before applying a
patch:

```text
planning preview API -> patch preview API -> approval API -> apply/validate API
```

That keeps mutation behind a later explicit approval boundary.

## Files Added Or Updated

### `src/repopilot/api/patches.py`

Defines `POST /repositories/patch-preview`.

The route builds context, creates a deterministic plan, reads relevant files
through safe read-only tools, creates a deterministic patch proposal, and returns
bounded previews.

### `src/repopilot/schemas/patches.py`

Defines:

- `PatchPreviewRequest`
- `ProposedFileChangePreview`
- `PatchProposalPreviewResponse`
- `PatchPreviewResponse`

### `src/repopilot/main.py`

Includes the patch preview router in the FastAPI app.

### `tests/test_patch_preview_api.py`

Tests successful previews, context metadata, plan and proposal fields, approval
requirements, preview truncation, relative paths, validation errors, missing
roots, deterministic output, omitted hashes, bounded content, and no LLM,
command, patch application, or write side effects.

### `README.md`

Documents the endpoint, example request body, and the fact that it does not apply
patches.

## How To Explain This In An Interview

You can explain this feature like this:

"I added a safe patch preview API that composes RepoPilot's deterministic
context builder, planner, read-only file tools, and patch proposal layer. Given a
repository path and issue, it returns context metadata, a plan, and a bounded
preview of the proposed changes. It requires approval, exposes only truncated
content previews, and never calls LLMs, applies patches, runs commands, or writes
files. This creates the review step before future approval and patch application
endpoints."
