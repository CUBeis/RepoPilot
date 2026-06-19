# Learning Note 30: Repair Apply Report API

## What Was Built

Milestone 31 adds a safe read-only FastAPI endpoint:

```text
POST /reports/repair-apply-result
```

The endpoint accepts an issue, a repair summary, and a previously returned
`RepairApplyResponse` payload. It returns a clean structured report and a
Markdown summary suitable for demos, frontend clients, or PR descriptions.

## Why Reporting Is Separate From Repair Application

Repair application is a mutating workflow. Reporting is an observation workflow.

Keeping them separate matters because:

- a caller can apply a repair once and summarize it many times
- reporting can be tested without touching the filesystem
- API clients can render a friendly summary without rerunning tools
- future PR-summary generation has a stable input shape

This endpoint assumes the repair apply workflow already happened elsewhere.

## Why This Endpoint Is Read-Only

The endpoint only summarizes supplied JSON data.

It does not:

- apply patches
- run validation commands
- call LLMs
- generate repair proposals
- start self-correction
- read files
- write files
- call failure analysis

That makes it safe to expose after the repair apply endpoint without creating a
new mutation boundary.

## How It Summarizes Direct Apply Results

When the supplied `RepairApplyResponse` has no validation result, the endpoint
returns:

```json
{
  "status": "repair_applied",
  "validation_ran": false,
  "validation_passed": null
}
```

It also extracts changed files from the supplied `applied_files` list and
includes them in both the structured response and Markdown.

## How It Summarizes Apply-And-Validate Results

When validation exists and passed, the endpoint returns:

```json
{
  "status": "repair_applied_validation_passed",
  "validation_ran": true,
  "validation_passed": true
}
```

When validation exists and failed, the endpoint returns:

```json
{
  "status": "repair_applied_validation_failed",
  "validation_ran": true,
  "validation_passed": false
}
```

Failed checks are copied only from validation checks where `passed=false`.

## Why Command Output Is Omitted

Repair apply responses can include bounded stdout and stderr previews from
validation checks. This reporting endpoint intentionally omits those fields.

The report includes only:

- failed check name
- command
- return code
- timeout state

That keeps the report concise and avoids exposing command output again through a
separate reporting endpoint.

## Why It Does Not Rerun Validation Or Analyze Failures

Validation execution and failure analysis are separate workflows. This endpoint
does not call `apply_and_validate_patch()` or `analyze_validation_result()`.

It simply reports what the caller supplied. That keeps the API deterministic and
prevents a reporting request from unexpectedly running commands.

## How This Completes The Visible Repair Workflow

RepoPilot now has a visible repair path:

```text
repair approval request -> approved repair apply -> repair apply report
```

The final report gives a human-readable summary of what changed and whether
validation ran, without hiding any new action behind the report request.

## Files Added Or Updated

### `src/repopilot/api/repair_reports.py`

Defines `POST /reports/repair-apply-result`.

The route derives status, changed files, validation metadata, failed checks, and
Markdown from a supplied `RepairApplyResponse`.

### `src/repopilot/schemas/repair_reports.py`

Defines:

- `RepairApplyReportRequest`
- `RepairReportFailedCheckResponse`
- `RepairApplyReportResponse`

The request validates non-blank issue and repair summary fields.

### `src/repopilot/main.py`

Includes the repair report router in the FastAPI app.

### `tests/test_repair_apply_report_api.py`

Tests direct repair reports, validation-passed reports, validation-failed
reports, failed check extraction, Markdown content, request validation, no
old/new content exposure, no validation output exposure, no execution side
effects, no filesystem access, and deterministic output.

### `README.md`

Documents `POST /reports/repair-apply-result`, a sample request body, and the
fact that the endpoint is reporting-only and does not mutate files.

## How To Explain This In An Interview

You can explain this feature like this:

"I added a read-only reporting API for repair apply results. It accepts a
previously returned RepairApplyResponse and turns it into structured status
fields plus a Markdown summary. It distinguishes direct apply from
apply-and-validate results, extracts changed files and failed checks, and omits
old/new content and command output. It does not apply patches, rerun validation,
call LLMs, generate repairs, or analyze failures. This completes the visible
repair workflow with a safe reporting surface."
