# RepoPilot v1.0 Release Checklist

This checklist prepares RepoPilot for public GitHub presentation as a portfolio
project. It does not add new workflow behavior.

## Release Target

- Version label: `v1.0.0`
- Release date: 2026-06-19
- Release type: portfolio/demo backend
- Audience: recruiters, engineering managers, AI engineering interviewers, and
  developers reviewing agentic AI architecture

## Public Presentation Checklist

- README has a clear elevator pitch.
- README explains what RepoPilot does.
- README explains why RepoPilot is safe.
- README lists API endpoints by category.
- README includes quickstart commands.
- README links to demo, API, interview, and architecture docs.
- Demo guide includes 3-minute and 7-minute flows.
- API examples include small request payloads.
- Interview script answers common architecture and safety questions.
- Architecture summary explains modules and workflow diagrams.
- Changelog includes a `v1.0.0` section.

## QA Checklist

Run from `D:\RepoPilot`:

```powershell
python -m pytest
python -m ruff check .
```

Expected state:

- pytest passes.
- Ruff passes.
- No product behavior changes were introduced during release prep.
- Documentation files render as Markdown on GitHub.

## Demo Checklist

Start the app:

```powershell
uvicorn repopilot.main:app --reload
```

Open:

```text
http://127.0.0.1:8000/docs
```

Recommended demo path:

1. `GET /health`
2. `GET /demo/workflow`
3. `POST /reports/workflow`
4. `POST /repositories/scan-summary`
5. `POST /repositories/context-preview`
6. `POST /repositories/plan-preview`
7. `POST /repositories/patch-preview`

Avoid live mutating endpoints unless using a temporary sandbox repository.

## Safety Checklist

- Read-only endpoints do not mutate repositories.
- Patch and repair apply endpoints require explicit approval.
- Commands are allowlisted and do not use shell execution.
- Report endpoints do not run tools.
- Repair generation and repair application remain separate.
- Self-correction does not happen automatically.
- No API endpoint calls real LLM providers.

## Suggested GitHub Metadata

Description:

```text
Production-style Agentic AI software engineer backend with safe repository analysis, planning, patch approval, validation, repair workflows, and PR-ready reporting.
```

Topics:

```text
agentic-ai
ai-engineering
fastapi
pydantic
pytest
ruff
software-engineering-agent
code-retrieval
human-in-the-loop
llm-tools
```

## Pre-Release Notes

Before tagging a real GitHub release:

- Review `git status`.
- Commit documentation and final QA changes.
- Run tests and Ruff one final time.
- Push to GitHub.
- Create a GitHub release tagged `v1.0.0`.
- Include the changelog summary in the release notes.
