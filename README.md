# RepoPilot

RepoPilot is a production-grade portfolio project for an agentic AI software
engineer. The long-term goal is a coding assistant that can ingest repositories,
retrieve relevant code, plan safe changes, edit files, run checks, self-correct,
and produce PR-ready summaries.

The current version establishes a clean Python project skeleton, adds a
deterministic repository scanner, introduces line-based code chunking, and adds a
keyword search retriever. It also composes them into a repository context
builder, deterministic planning layer, and provider-independent LLM client
abstraction. It can also create plans through an injected LLM client using a
fake deterministic client in tests, read files through safe read-only tools, and
prepare approval-gated patch proposals, including proposals generated through
the LLM client abstraction, and safely apply approved proposals. These pieces
are intentionally separate from any real LLM, embedding, vector database,
autonomous file editing agent, test execution, or shell execution logic.
It now includes a safe command runner foundation for approved validation
commands, but it still does not self-correct or run autonomous agent loops.
The current validation pipeline can apply an approved patch and run allowlisted
checks, then report the result without attempting repairs.

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

## Keyword Retriever

Milestone 4 adds deterministic keyword retrieval:

- Accepts a list of `CodeChunk` objects and a natural language query
- Tokenizes query, paths, and chunk text
- Ignores case and simple punctuation
- Scores path matches higher than text matches
- Returns ranked chunks with score and matched terms
- Handles empty queries and empty chunk lists safely

Example usage:

```python
from repopilot.retrieval import retrieve_keyword_chunks

results = retrieve_keyword_chunks(chunks, "auth login route", top_k=3)
for result in results:
    print(result.score, result.chunk.path, result.matched_terms)
```

## Repository Context Builder

Milestone 5 composes scanner, chunker, and keyword retrieval:

- Scans a repository
- Chunks every scanned file
- Retrieves relevant chunks for a natural language query
- Returns scan summary, total chunk count, and ranked retrieved chunks

Example usage:

```python
from repopilot.context import build_repository_context

context = build_repository_context("D:/RepoPilot", "repository scanner")
print(context.scanned_file_count, context.total_chunks)
for result in context.retrieved_chunks:
    print(result.score, result.chunk.path, result.matched_terms)
```

## Planning Layer

Milestone 6 turns repository context into a structured implementation plan:

- Accepts a user issue and `RepositoryContext`
- Builds a deterministic planning prompt
- Returns objective, relevant files, ordered steps, risks, assumptions, and
  confidence
- Works without any external LLM API key
- Does not edit files or run tests

Example usage:

```python
from repopilot.context import build_repository_context
from repopilot.planning import create_implementation_plan

issue = "Fix repository scanner handling for empty files"
context = build_repository_context("D:/RepoPilot", issue)
plan = create_implementation_plan(issue, context)
print(plan.objective, plan.confidence)
for step in plan.steps:
    print(step.order, step.description, step.target_files)
```

## LLM Client Abstraction

Milestone 7 adds provider-independent LLM request and response models, a client
protocol, and a deterministic fake client:

- Defines `LLMMessage`, `LLMRequest`, `LLMUsage`, and `LLMResponse`
- Defines an `LLMClient` protocol
- Includes `FakeLLMClient` for tests and local development
- Does not call external APIs or require API keys

Example usage:

```python
from repopilot.llm import FakeLLMClient, LLMMessage, LLMRequest

client = FakeLLMClient("Deterministic response")
request = LLMRequest(
    messages=[LLMMessage(role="user", content="Create a plan")],
    model="fake-planner",
)
response = client.generate(request)
print(response.content, response.usage)
```

## LLM-Backed Planner

Milestone 8 adds an LLM-backed planner that works with any `LLMClient`:

- Builds the existing planning prompt
- Sends an `LLMRequest` through the provided client
- Expects JSON response content
- Parses and validates the JSON into `ImplementationPlan`
- Works with `FakeLLMClient` for deterministic tests

Example usage:

```python
import json

from repopilot.context import build_repository_context
from repopilot.llm import FakeLLMClient
from repopilot.planning import create_llm_implementation_plan

fake_response = json.dumps({
    "objective": "Fix login bug",
    "relevant_files": ["src/auth.py"],
    "steps": [{
        "order": 1,
        "description": "Inspect the login function.",
        "target_files": ["src/auth.py"],
    }],
    "risks": ["May affect authentication flow."],
    "assumptions": ["Retrieved chunks are relevant."],
    "confidence": 0.8,
})

context = build_repository_context("D:/RepoPilot", "Fix login bug")
client = FakeLLMClient(fake_response)
plan = create_llm_implementation_plan("Fix login bug", context, client)
print(plan.objective, plan.confidence)
```

## Read-Only File Tools

Milestone 9 adds safe read-only filesystem tools:

- Accept a repository root and relative file path
- Reject absolute paths and path traversal
- Read UTF-8 text files only
- Support whole-file reads and line-range reads
- Enforce size and line-count limits
- Return structured metadata with POSIX-style relative paths

Example usage:

```python
from repopilot.tools import read_text_file_lines

result = read_text_file_lines("D:/RepoPilot", "README.md", 1, 10)
print(result.path, result.start_line, result.end_line)
print(result.content)
```

## Patch Proposal Layer

Milestone 10 adds structured patch proposals without writing files:

- Accepts an `ImplementationPlan` and read-only `FileReadResult` objects
- Validates that planned target files were actually read
- Rejects reads for files outside the plan
- Preserves original content until a future editing layer exists
- Requires approval before any future patch application

Example usage:

```python
from repopilot.patching import create_patch_proposal
from repopilot.planning import create_implementation_plan
from repopilot.context import build_repository_context
from repopilot.tools import read_text_file

issue = "Update README setup guidance"
context = build_repository_context("D:/RepoPilot", issue)
plan = create_implementation_plan(issue, context)
file_reads = [read_text_file("D:/RepoPilot", path) for path in plan.relevant_files]

proposal = create_patch_proposal(plan, file_reads)
print(proposal.summary, proposal.requires_approval)
```

## LLM Patch Proposal Generator

Milestone 11 adds an LLM-backed patch proposal generator that works with any
`LLMClient`:

- Builds a prompt from an `ImplementationPlan` and read-only file results
- Sends an `LLMRequest` through the provided client
- Expects JSON response content
- Parses and validates that JSON into `PatchProposal`
- Forces `requires_approval=True`
- Does not write files or apply patches

Example usage with `FakeLLMClient`:

```python
import json

from repopilot.llm import FakeLLMClient
from repopilot.patching import create_llm_patch_proposal

fake_response = json.dumps({
    "summary": "Update login behavior.",
    "target_files": ["src/auth.py"],
    "changes": [{
        "path": "src/auth.py",
        "reason": "Make login return success.",
        "start_line": 1,
        "end_line": 2,
        "original_content": "def login_user():\n    return False\n",
        "proposed_content": "def login_user():\n    return True\n",
    }],
    "risks": ["May affect authentication flow."],
    "requires_approval": False,
})

client = FakeLLMClient(fake_response)
proposal = create_llm_patch_proposal(plan, file_reads, client)
print(proposal.requires_approval)
```

## Safe Patch Applier

Milestone 12 adds safe patch application for approved proposals:

- Requires explicit approval before writing
- Refuses proposals that do not require approval
- Validates relative paths stay inside the repository root
- Rejects missing files, directories, absolute paths, and path traversal
- Applies only when current file content exactly matches `original_content`
- Writes UTF-8 `proposed_content` only after every change is validated

Example usage:

```python
from repopilot.patching import apply_patch_proposal

result = apply_patch_proposal(
    "D:/RepoPilot",
    proposal,
    approved=True,
)
print(result.changed_file_count)
```

## Safe Command Runner

Milestone 13 adds a constrained command runner for validation commands:

- Runs commands with `cwd` set to the repository root
- Uses `subprocess.run` without `shell=True`
- Captures stdout and stderr as text
- Enforces timeouts
- Allows only exact commands from an allowlist
- Returns a structured `CommandResult`
- Does not self-correct or interpret failures

Default allowlist:

```python
["pytest"]
["ruff", "check", "."]
["ruff", "format", "--check", "."]
```

Example usage:

```python
from repopilot.tools import run_command

result = run_command("D:/RepoPilot", ["pytest"])
print(result.return_code)
print(result.stdout)
```

## Patch Validation Pipeline

Milestone 14 composes approved patch application with validation commands:

- Applies a `PatchProposal` through the safe patch applier
- Runs validation commands only after the patch applies successfully
- Uses the safe command runner for every command
- Allows only the requested validation commands
- Marks checks passed when return code is `0` and the command did not time out
- Does not self-correct or call an LLM

Default validation commands:

```python
["pytest"]
["ruff", "check", "."]
```

Example usage:

```python
from repopilot.validation import apply_and_validate_patch

result = apply_and_validate_patch(
    "D:/RepoPilot",
    proposal,
    approved=True,
)
print(result.passed)
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
- Deterministic keyword search retriever
- Deterministic repository context builder
- Deterministic structured planning layer
- Provider-independent LLM client abstraction
- Deterministic fake LLM client
- LLM-backed planner using injected fake/test clients
- Safe read-only file tools
- Approval-gated patch proposal layer
- LLM-backed patch proposal generator using injected fake/test clients
- Safe patch applier for explicitly approved proposals
- Safe command runner for allowlisted validation commands
- Patch validation pipeline for apply -> validate workflows

Not included yet:

- Embedding retrieval
- Real LLM provider calls
- Vector database
- Autonomous file editing agent
- Test self-correction loop
