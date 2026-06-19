# Learning Note 31: Workflow Report API

## What Was Built

Milestone 32 adds a safe read-only FastAPI endpoint:

```text
POST /reports/workflow
```

The endpoint accepts supplied workflow payloads and turns them into one
PR-ready report. It does not execute any workflow step.

## Why A Unified Workflow Report Is Useful

RepoPilot now has many safe pieces:

- planning previews
- patch proposal previews
- patch application
- validation
- failure analysis
- repair approval
- repair application
- repair apply reporting

A unified workflow report gives clients one clean summary of where a run stands.
That is useful for demos, API consumers, frontend screens, logs, and future pull
request descriptions.

## Why This Endpoint Is Read-Only

The endpoint only summarizes data supplied in the request.

It does not:

- scan repositories
- build context
- create plans
- apply patches
- run commands
- call LLMs
- generate repairs
- start self-correction
- read files
- write files
- analyze failures

This keeps reporting separate from execution.

## How Status Priority Works

The endpoint chooses the most advanced workflow state with this priority:

1. `repair_apply_report.status`
2. `repair_waiting_for_approval` if a repair approval exists
3. `validation_failed_needs_repair` if failure analysis needs self-correction
4. `validation_passed` or `validation_failed` from validation results
5. `patch_applied` if an apply result exists
6. `patch_proposed` if a patch proposal exists
7. `planned` if a plan exists
8. `issue_received`

This makes the report deterministic even when multiple objects are supplied.

## What Fields Are Derived

The report derives:

- planned files from the plan
- proposed files from patch proposals and repair approvals
- changed files from repair apply reports, apply results, or validation results
- validation state from repair apply reports, validation results, or repair apply
  results
- failed check count from repair apply reports, failure analysis, or validation
  checks
- repair and approval flags from repair approval and apply payloads

The Markdown summary uses the same derived fields.

## Why Sensitive Details Are Omitted

The response intentionally excludes:

- `old_content`
- `new_content`
- `original_content`
- `proposed_content`
- `stdout_preview`
- `stderr_preview`
- `stdout_excerpt`
- `stderr_excerpt`

Those details belong in lower-level workflow payloads, not in a PR-ready summary.
The unified report stays concise and safe to show in demos.

## How This Completes The Reporting Surface

Earlier endpoints report individual workflow moments. This endpoint reports the
whole visible workflow state.

The path is now:

```text
plan -> propose -> apply -> validate -> analyze -> repair approval -> repair apply -> workflow report
```

Each stage remains explicit, and reporting never triggers hidden action.

## Files Added Or Updated

### `src/repopilot/api/workflow_reports.py`

Defines `POST /reports/workflow`.

The route derives status, files, validation state, repair flags, and Markdown
from supplied payloads.

### `src/repopilot/schemas/workflow_reports.py`

Defines:

- `WorkflowReportRequest`
- `WorkflowReportResponse`

The request reuses existing API response schemas where possible.

### `src/repopilot/main.py`

Includes the workflow report router in the FastAPI app.

### `tests/test_workflow_report_api.py`

Tests every status, derived fields, Markdown output, blank issue validation,
deterministic behavior, hidden-side-effect guards, and omission of old/new
content and validation output previews.

### `README.md`

Documents `POST /reports/workflow`, an example request body, and the reporting-
only safety boundary.

## How To Explain This In An Interview

You can explain this feature like this:

"I added a unified workflow reporting API that accepts already-created RepoPilot
workflow payloads and produces one PR-ready summary. It applies a deterministic
status priority, extracts planned/proposed/changed files, summarizes validation
and repair state, and returns Markdown. It deliberately does not scan repos,
plan, apply patches, run commands, call LLMs, generate repairs, or expose
old/new file contents or command output. This separates observability from
execution and gives the project a clean final reporting surface."
