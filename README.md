# RepoPilot

RepoPilot is a production-grade portfolio project for an agentic AI software
engineer: a coding assistant backend that can inspect a repository, retrieve
relevant code, plan changes, propose patches, apply approved edits, validate
with allowlisted commands, prepare repairs, and generate PR-ready reports.

The project is intentionally built in small, safe milestones. Most endpoints are
read-only previews or reports. Mutating endpoints require explicit approval, and
command execution is allowlisted.

## Elevator Pitch

RepoPilot demonstrates the engineering architecture behind a real AI coding
agent without hiding unsafe behavior behind a chatbot. It separates repository
understanding, planning, patch proposal, approval, application, validation,
failure analysis, repair approval, and reporting into testable modules with
clear safety boundaries.

## What RepoPilot Does

- Scans local repositories and returns safe file metadata.
- Chunks source files deterministically for future retrieval and RAG.
- Retrieves relevant chunks with explainable keyword scoring.
- Builds repository context for an issue.
- Creates deterministic implementation plans.
- Provides provider-independent LLM client abstractions with fake clients for
  tests.
- Proposes patches without applying them.
- Applies patches only after explicit approval.
- Runs validation commands only through an allowlist.
- Analyzes validation failures into structured summaries.
- Prepares repair proposals for human approval.
- Produces workflow reports suitable for demos, APIs, and PR summaries.

## Why It Is Safe

RepoPilot is designed around explicit boundaries:

- **Read-only previews:** scan, context, plan, and patch preview endpoints do not
  mutate repositories.
- **Approval-gated mutation:** patch and repair apply endpoints require
  `approved=true` and proposals that require approval.
- **Command allowlisting:** validation commands run only when they match an
  allowed command list.
- **No hidden self-correction:** repair generation, approval, application, and
  validation are separate steps.
- **Bounded outputs:** preview text and command output are truncated before being
  returned through APIs.
- **Deterministic reporting:** report endpoints summarize supplied payloads and
  do not execute tools.
- **No real provider calls yet:** LLM-powered paths use injected clients and fake
  deterministic clients in tests.

## Quickstart

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install the project with development dependencies:

```powershell
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Run the FastAPI app:

```powershell
uvicorn repopilot.main:app --reload
```

Open:

```text
http://127.0.0.1:8000/docs
```

Run tests:

```powershell
python -m pytest
```

Run Ruff:

```powershell
python -m ruff check .
```

Run the CLI demo:

```powershell
repopilot report-demo
```

## Suggested Demo Path

Use Swagger at `http://127.0.0.1:8000/docs` and show this flow:

1. `GET /health`
2. `GET /demo/workflow`
3. `POST /reports/workflow`
4. `POST /repositories/scan-summary`
5. `POST /repositories/context-preview`
6. `POST /repositories/plan-preview`
7. `POST /repositories/patch-preview`

This path starts with safe demos and reporting, then shows repository
understanding, retrieval, planning, and patch preview without mutating files.

## API Endpoints

### Core And Demo

- `GET /health` - health check.
- `GET /demo/workflow` - deterministic in-memory successful workflow report.
- `GET /report-demo` - in-memory sample run report as JSON.
- `GET /report-demo/markdown` - in-memory sample run report as Markdown.

### Repository Understanding

- `POST /repositories/scan-summary` - read-only repository file metadata.
- `POST /repositories/context-preview` - read-only retrieved chunk previews.
- `POST /repositories/plan-preview` - deterministic implementation plan.
- `POST /repositories/patch-preview` - deterministic patch proposal preview.

### Patch Application And Validation

- `POST /patches/apply` - apply an approved patch proposal.
- `POST /patches/apply-and-validate` - apply an approved proposal and run
  allowlisted validation commands.
- `POST /validation/analyze-failures` - summarize supplied validation failures.

### Repair Workflow

- `POST /repairs/approval-request` - create a repair approval request from a
  failed attempt and fake LLM response JSON.
- `POST /repairs/apply-approved` - apply an approved repair proposal, optionally
  running validation.

### Reporting

- `POST /reports/repair-apply-result` - summarize a supplied repair apply
  result.
- `POST /reports/workflow` - summarize supplied workflow payloads into one
  PR-ready report.

## Documentation

- [Project brief](docs/project_brief.md)
- [Demo guide](docs/demo_guide.md)
- [API examples](docs/api_examples.md)
- [Interview script](docs/interview_script.md)
- [Architecture summary](docs/architecture_summary.md)
- [Learning notes](docs/learning_notes/)

## Portfolio Value

RepoPilot is impressive as a portfolio project because it demonstrates more than
prompting. It shows the backend architecture of an agentic coding system:

- deterministic repository analysis before LLM reasoning
- typed data contracts with Pydantic
- strict separation between planning, proposing, applying, validating, repairing,
  and reporting
- human approval checkpoints
- command execution safety
- deterministic fake LLM clients for testability
- extensive tests across API and core layers
- clear documentation for demos and interviews

## Current Limitations

RepoPilot does not yet include real provider integrations, embeddings, a vector
database, a frontend, authentication, Docker deployment, or autonomous
end-to-end repair generation. Those are intentionally deferred until the safety
contracts and deterministic workflow layers are solid.
