# Learning Note 20: Reporting API Endpoints

## What Was Built

Milestone 21 adds safe FastAPI endpoints for RepoPilot's reporting layer:

```text
GET /report-demo
GET /report-demo/markdown
```

`/report-demo` returns a sample `AgentRunReport` as JSON.

`/report-demo/markdown` returns the same sample report as plain text Markdown.

## Why API Endpoints Are Useful For Demos

API endpoints make RepoPilot easier to demonstrate beyond the command line. A
reviewer can start the FastAPI app, open `/docs`, and call reporting endpoints
from the browser.

This shows that RepoPilot's internal reporting model is ready to serve future
frontends, demos, and integrations.

## Why The First API Endpoints Are Read-Only And In-Memory

The first reporting API endpoints do not run real agent workflows. They build a
small sample report in memory.

They do not:

- scan repositories
- read files
- write files
- run commands
- call LLMs
- apply patches

This keeps the API safe while still demonstrating useful output.

## How They Reuse The Reporting Layer

The endpoints call the shared sample report helper:

```python
create_sample_agent_run_report()
```

That helper builds sample Pydantic objects and calls:

```python
create_agent_run_report(...)
```

The CLI demo and API demo use the same helper, so they show the same kind of
report without duplicating sample construction.

## Why They Do Not Execute Agent Tools Yet

Real workflow endpoints will need more safety design:

- input validation
- repository path validation
- approval checkpoints
- command allowlists
- authentication
- audit logs

This milestone intentionally avoids those concerns. It exposes only a safe demo
report.

## How This Prepares For Future Workflow Endpoints

The app now has a reporting router and response schema. Future endpoints can
follow the same pattern:

```text
route -> safe application layer -> typed schema response
```

Later endpoints might expose repository scan summaries, context-building
results, approval requests, validation results, or final PR summaries.

## Files Added Or Updated

### `src/repopilot/api/reporting.py`

Defines the reporting API router.

It provides:

- `GET /report-demo`
- `GET /report-demo/markdown`

### `src/repopilot/schemas/reporting.py`

Defines `ReportDemoResponse`, the response schema for the JSON demo endpoint.

### `src/repopilot/main.py`

Includes the reporting router in the FastAPI app.

### `src/repopilot/reporting/demo.py`

Provides the shared in-memory sample report helper used by both the CLI and API.

### `src/repopilot/cli.py`

Now reuses `create_sample_agent_run_report()` instead of building its own sample
report inline.

### `tests/test_reporting_api.py`

Tests JSON and Markdown endpoints, deterministic output, and no calls to LLMs,
commands, patch application, or repository scanning.

### `README.md`

Documents:

- `/docs`
- `/report-demo`
- `/report-demo/markdown`

## How To Explain This In An Interview

You can explain this feature like this:

"I exposed RepoPilot's reporting layer through safe FastAPI demo endpoints. One
endpoint returns a sample AgentRunReport as JSON, and another returns the same
report as Markdown. Both are read-only and in-memory, so they do not scan repos,
call LLMs, run commands, or apply patches. This demonstrates how the backend can
serve agent run summaries while preserving the safety boundary before real
workflow endpoints are added."
