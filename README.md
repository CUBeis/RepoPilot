# RepoPilot

RepoPilot is a production-grade portfolio project for an agentic AI software
engineer. The long-term goal is a coding assistant that can ingest repositories,
retrieve relevant code, plan safe changes, edit files, run checks, self-correct,
and produce PR-ready summaries.

The current version establishes a clean Python project skeleton, adds a
deterministic repository scanner, and introduces line-based code chunking. These
pieces are intentionally separate from any LLM, embedding, vector database, or
agent logic.

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

## Repository Scanner

Milestone 2 adds deterministic local repository scanning:

- Validates that a root path exists and is a directory
- Recursively scans supported text files
- Ignores generated or noisy folders such as `.git`, `.venv`, and `node_modules`
- Skips unsupported, binary, and oversized files
- Returns relative paths and metadata such as language, size, line count, and
  SHA-256 hash

Example usage:

```python
from repopilot.repository import scan_repository

result = scan_repository("D:/RepoPilot")
print(result.file_count)
```

## Code Chunker

Milestone 3 adds deterministic line-based chunking:

- Accepts a repository root and a scanned file
- Reads text files safely
- Splits files into fixed-size line chunks
- Includes configurable line overlap between chunks
- Returns relative paths, line ranges, chunk index, text, and SHA-256 hash
- Skips empty files

Example usage:

```python
from repopilot.chunking import chunk_file
from repopilot.repository import scan_repository

scan = scan_repository("D:/RepoPilot")
chunks = chunk_file("D:/RepoPilot", scan.files[0])
print(chunks[0].path, chunks[0].start_line, chunks[0].end_line)
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
- Deterministic repository scanner
- Deterministic line-based code chunker

Not included yet:

- Code indexing
- Retrieval
- LLM calls
- Vector database
- File editing agent
- Test self-correction loop
