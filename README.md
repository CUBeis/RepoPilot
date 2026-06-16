# RepoPilot

RepoPilot is a production-grade portfolio project for an agentic AI software
engineer. The long-term goal is a coding assistant that can ingest repositories,
retrieve relevant code, plan safe changes, edit files, run checks, self-correct,
and produce PR-ready summaries.

This first version is intentionally small. It establishes a clean Python project
skeleton with a FastAPI backend, typed configuration, Pydantic schemas, Ruff, and
pytest.

## Requirements

- Python 3.11+

## Documentation

- Project brief: `docs/project_brief.md`
- Learning notes: `docs/learning_notes/`

## Setup

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

Optional: copy `.env.example` to `.env` and adjust values for your local
environment.

## Run The App

Start the FastAPI development server:

```powershell
uvicorn repopilot.main:app --reload
```

Open the health endpoint:

```text
http://127.0.0.1:8000/health
```

Expected response:

```json
{
  "status": "ok",
  "service": "RepoPilot",
  "version": "0.1.0"
}
```

## Run Tests

```powershell
pytest
```

## Run Ruff

Check linting:

```powershell
ruff check .
```

Format code:

```powershell
ruff format .
```

## Current Scope

Included:

- FastAPI app factory
- `/health` endpoint
- Pydantic response schema
- Environment-based settings
- Pytest health endpoint test
- Ruff configuration
- Example environment file
- Python `.gitignore`

Not included yet:

- Repository ingestion
- Code indexing
- Retrieval
- LLM calls
- Vector database
- File editing agent
- Test self-correction loop
