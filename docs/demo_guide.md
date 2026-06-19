# RepoPilot Demo Guide

This guide helps you present RepoPilot as a portfolio project. The goal is to
show a safe agentic coding workflow without mutating a real repository during
the first demo pass.

## Before The Demo

Start the API:

```powershell
uvicorn repopilot.main:app --reload
```

Open Swagger:

```text
http://127.0.0.1:8000/docs
```

Keep a terminal ready for:

```powershell
python -m pytest
python -m ruff check .
```

## What To Say First

"RepoPilot is not a chatbot wrapper. It is a backend architecture for an
agentic AI software engineer. It breaks the workflow into safe, typed steps:
scan, retrieve, plan, propose, approve, apply, validate, repair, and report."

Then emphasize:

- previews are read-only
- mutation is approval-gated
- commands are allowlisted
- reports are deterministic and side-effect free

## What To Click In Swagger

### 1. `GET /health`

Use this first to prove the API is running.

Say:

"I start with a production habit: a health endpoint that proves the backend is
alive and versioned."

### 2. `GET /demo/workflow`

Use this as the main safe demo.

Say:

"This is a complete successful workflow report built entirely in memory. It
shows the final product experience without scanning files, applying patches, or
running commands."

Point out:

- status is `validation_passed`
- planned files are present
- proposed files are present
- changed files are present
- validation ran and passed
- Markdown summary is PR-friendly

### 3. `POST /reports/workflow`

Show that clients can supply workflow payloads and get a unified report.

Say:

"This endpoint is reporting only. It summarizes supplied data and does not run
agent tools."

### 4. `POST /repositories/scan-summary`

Use a local repo path, such as:

```json
{
  "root_path": "D:/RepoPilot"
}
```

Say:

"This is the first real repository-understanding step. It returns metadata, not
file contents."

### 5. `POST /repositories/context-preview`

Example:

```json
{
  "root_path": "D:/RepoPilot",
  "query": "safe patch apply",
  "top_k": 5,
  "max_preview_chars": 500
}
```

Say:

"This composes scan, chunk, and keyword retrieval to find useful context before
LLM planning."

### 6. `POST /repositories/plan-preview`

Example:

```json
{
  "root_path": "D:/RepoPilot",
  "issue": "Improve safe patch apply docs",
  "top_k": 5
}
```

Say:

"Planning is separate from editing. This endpoint returns a deterministic plan
without proposing or applying changes."

### 7. `POST /repositories/patch-preview`

Example:

```json
{
  "root_path": "D:/RepoPilot",
  "issue": "Improve safe patch apply docs",
  "top_k": 5,
  "max_preview_chars": 500
}
```

Say:

"Patch preview reads files only through safe read-only tools and returns bounded
previews. It still does not write anything."

## Three-Minute Demo Flow

1. Open `/docs`.
2. Run `GET /health`.
3. Run `GET /demo/workflow`.
4. Point at the Markdown summary.
5. Run `POST /repositories/context-preview`.
6. Close with the safety pitch.

Suggested closing:

"The important part is the shape: the system can prepare context, plan, propose,
validate, repair, and report, but every risky step is explicit and tested."

## Seven-Minute Demo Flow

1. Open `/docs`.
2. Run `GET /health`.
3. Run `GET /demo/workflow`.
4. Run `POST /reports/workflow` with a small sample payload.
5. Run `POST /repositories/scan-summary`.
6. Run `POST /repositories/context-preview`.
7. Run `POST /repositories/plan-preview`.
8. Run `POST /repositories/patch-preview`.
9. Explain approval-gated apply endpoints without invoking them on a real repo.
10. Show terminal test output with `python -m pytest`.

## Demo Tips

- Start with the in-memory demo before touching a real path.
- Say "read-only" every time you show preview endpoints.
- Say "approval-gated" before discussing apply endpoints.
- Mention that fake LLM clients make tests deterministic.
- Avoid live mutation unless you prepare a temporary sandbox repository.
