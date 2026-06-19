# Learning Note 32: Demo Workflow API

## What Was Built

Milestone 33 adds a deterministic FastAPI demo endpoint:

```text
GET /demo/workflow
```

The endpoint returns a complete in-memory `WorkflowReportResponse` that shows a
successful RepoPilot flow:

```text
plan -> patch proposed -> applied -> validation passed -> workflow report
```

It is designed for demos, API docs, and portfolio walkthroughs.

## Why The Demo Is Fully In-Memory

The endpoint builds fixed sample payloads with existing response schemas. It does
not inspect a real repository or execute any agent tool.

That keeps the demo:

- deterministic
- fast
- safe to call repeatedly
- easy to show in `/docs`
- independent of local files or commands

## What It Reuses

The endpoint reuses the same workflow report builder used by:

```text
POST /reports/workflow
```

That means the demo and the real reporting endpoint share the same status,
derived field, and Markdown logic.

## What The Demo Shows

The fixed sample includes:

- a realistic issue
- planned files
- proposed files
- changed files
- validation that ran and passed
- a Markdown workflow report

The returned status is:

```text
validation_passed
```

## Safety Boundary

The endpoint does not:

- scan repositories
- build context
- read files
- write files
- apply patches
- run validation commands
- call LLMs
- generate repairs
- start self-correction
- analyze failures

It returns only constructed sample data.

## Why Sensitive Details Are Not Exposed

The demo response uses the same safe report response as the workflow report API.
It does not expose:

- old file content
- new file content
- proposal content previews
- stdout previews
- stderr previews

This keeps the demo output focused on workflow state instead of raw internal
payload details.

## Files Added Or Updated

### `src/repopilot/api/demo.py`

Defines `GET /demo/workflow`.

The route builds fixed in-memory workflow payloads and calls the shared workflow
report builder.

### `src/repopilot/api/workflow_reports.py`

Adds `build_workflow_report()` so both the POST workflow report endpoint and the
demo endpoint reuse the same report logic.

### `src/repopilot/main.py`

Includes the demo router in the FastAPI app.

### `tests/test_demo_workflow_api.py`

Tests the endpoint status, core response fields, Markdown, deterministic output,
omitted sensitive fields, and absence of hidden workflow execution or filesystem
access.

### `README.md`

Documents `GET /demo/workflow` and explains that it is fully in-memory and safe
for demos.

## How To Explain This In An Interview

You can explain this feature like this:

"I added a deterministic demo workflow endpoint that returns a complete
successful RepoPilot workflow report without running any tools. It builds fixed
sample payloads in memory, reuses the same workflow report builder as the real
reporting endpoint, and returns a PR-ready Markdown summary. It does not scan
repos, read files, apply patches, run commands, call LLMs, generate repairs, or
self-correct. This gives the project a safe live demo surface for FastAPI docs
and portfolio walkthroughs."
