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
the LLM client abstraction, and safely apply approved proposals. It now includes
a safe command runner for approved validation commands, a validation pipeline,
structured failure analysis, and a bounded self-correction orchestrator that can
try supplied repair proposals. It can also ask an injected `LLMClient` to
produce a repair `PatchProposal` from a failed attempt, failure analysis, and
read-only file context, then package that repair as an approval request. These
pieces can also be summarized into structured run reports for CLI, API, demo,
or PR-summary use. They are intentionally separate from any real LLM, embedding,
vector database, autonomous file editing agent, arbitrary shell execution, or
unapproved patch application.

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

Open the interactive API docs:

```text
http://127.0.0.1:8000/docs
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

## Run CLI Demo

Print a sample RepoPilot run report without scanning repositories, calling LLMs,
running commands, or writing files:

```powershell
repopilot report-demo
```

## Run Reporting API Demo

With the FastAPI server running, open the safe in-memory reporting demos:

```text
http://127.0.0.1:8000/report-demo
http://127.0.0.1:8000/report-demo/markdown
```

## Run Repository Scan API Demo

With the FastAPI server running, request a safe read-only scan summary:

```text
POST http://127.0.0.1:8000/repositories/scan-summary
```

Example JSON body:

```json
{
  "root_path": "D:/RepoPilot"
}
```

## Run Context Preview API Demo

With the FastAPI server running, request bounded retrieved chunk previews:

```text
POST http://127.0.0.1:8000/repositories/context-preview
```

Example JSON body:

```json
{
  "root_path": "D:/RepoPilot",
  "query": "repository scanner",
  "top_k": 5,
  "max_preview_chars": 500
}
```

## Run Planning Preview API Demo

With the FastAPI server running, request a deterministic implementation plan
preview:

```text
POST http://127.0.0.1:8000/repositories/plan-preview
```

Example JSON body:

```json
{
  "root_path": "D:/RepoPilot",
  "issue": "Improve repository scanner error handling",
  "top_k": 5
}
```

## Run Patch Preview API Demo

With the FastAPI server running, request a deterministic patch proposal preview:

```text
POST http://127.0.0.1:8000/repositories/patch-preview
```

Example JSON body:

```json
{
  "root_path": "D:/RepoPilot",
  "issue": "Improve repository scanner error handling",
  "top_k": 5,
  "max_preview_chars": 500
}
```

This endpoint creates a preview only. It does not apply patches.

## Run Patch Apply API Demo

With the FastAPI server running, apply an already reviewed patch proposal:

```text
POST http://127.0.0.1:8000/patches/apply
```

Example JSON body:

```json
{
  "root_path": "D:/RepoPilot",
  "approved": true,
  "proposal": {
    "summary": "Update app output.",
    "target_files": ["src/app.py"],
    "changes": [
      {
        "path": "src/app.py",
        "reason": "Reviewed change.",
        "start_line": 1,
        "end_line": 1,
        "original_content": "print('old')\n",
        "proposed_content": "print('new')\n"
      }
    ],
    "risks": ["May affect app output."],
    "requires_approval": true
  }
}
```

This endpoint mutates files only when `approved=true` and the proposal also
requires approval. Validation commands remain a separate workflow.

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

## Validation Failure Analyzer

Milestone 15 summarizes failed validation results for future self-correction:

- Accepts a `PatchValidationResult`
- Detects failed checks where `check.passed` is `False`
- Captures stdout and stderr excerpts
- Handles timeout failures clearly
- Returns whether future self-correction is needed
- Does not rerun commands, mutate files, call LLMs, or create repairs

Example usage:

```python
from repopilot.validation import analyze_validation_result

analysis = analyze_validation_result(result)
print(analysis.summary)
print(analysis.needs_self_correction)
```

## Self-Correction Orchestrator

Milestone 16 composes patch validation and failure analysis into a bounded retry
loop:

- Validates the initial patch proposal first
- Analyzes validation failures into structured summaries
- Optionally tries supplied repair proposals
- Stops when validation passes, `max_attempts` is reached, or no repair proposal
  is available
- Does not generate repairs, call LLMs, or expand command permissions

Example usage:

```python
from repopilot.agent import run_self_correction_loop

result = run_self_correction_loop(
    "D:/RepoPilot",
    proposal,
    approved=True,
    repair_proposals=[repair_proposal],
)
print(result.final_passed, result.stopped_reason)
```

## LLM Repair Proposal Generator

Milestone 17 turns a failed validation attempt into a new structured repair
proposal through an injected `LLMClient`:

- Accepts a failed `SelfCorrectionAttempt`
- Includes `FailureAnalysis` and read-only file context in the prompt
- Expects JSON that matches the existing `PatchProposal` schema
- Forces `requires_approval=True`
- Allows extra read-only context, but only permits proposed changes for files
  targeted by the failed attempt and actually read
- Does not apply patches, run commands, or call real providers

Example usage with `FakeLLMClient`:

```python
from repopilot.agent import create_llm_repair_proposal
from repopilot.llm import FakeLLMClient

client = FakeLLMClient(fake_repair_json)
repair_proposal = create_llm_repair_proposal(
    failed_attempt,
    file_reads,
    client,
)
print(repair_proposal.requires_approval)
```

## Approval-Gated Repair Workflow

Milestone 18 wraps generated repair proposals in an explicit approval request:

- Accepts a failed `SelfCorrectionAttempt`
- Calls the LLM repair proposal generator
- Returns a `RepairApprovalRequest`
- Always marks approval as required
- Does not apply patches, run validation commands, or call the self-correction
  loop

Example usage:

```python
from repopilot.agent import prepare_repair_for_approval

approval_request = prepare_repair_for_approval(
    failed_attempt,
    file_reads,
    client,
)
print(approval_request.approval_required)
print(approval_request.repair_proposal.summary)
```

## Agent Run Report

Milestone 19 turns RepoPilot outputs into a structured report suitable for CLI,
API, demos, and PR summaries:

- Accepts an issue plus optional plan, proposal, validation, failure,
  self-correction, and repair approval objects
- Derives a deterministic run status
- Extracts planned, proposed, and changed files
- Reports validation and approval state
- Produces a readable Markdown summary
- Does not call LLMs, run commands, read files, write files, or apply patches

Example usage:

```python
from repopilot.reporting import create_agent_run_report

report = create_agent_run_report(
    issue="Fix login bug",
    plan=plan,
    patch_proposal=proposal,
    validation_result=validation_result,
)
print(report.status)
print(report.markdown_summary)
```

## CLI Demo Command

Milestone 20 adds a small CLI entry point:

```powershell
repopilot report-demo
```

The command builds an in-memory sample run report and prints its Markdown
summary. It is read-only and does not execute agent tools.

## Reporting API Endpoints

Milestone 21 exposes the same kind of safe sample run report through FastAPI:

- `GET /report-demo` returns the sample `AgentRunReport` as JSON
- `GET /report-demo/markdown` returns the sample Markdown summary as plain text

Both endpoints are in-memory and do not scan repositories, read files, write
files, run commands, call LLMs, or apply patches.

## Repository Scan Summary API

Milestone 22 exposes the deterministic repository scanner through a safe
read-only endpoint:

- `POST /repositories/scan-summary`
- Accepts `root_path`
- Returns repository summary metadata and relative file summaries
- Omits SHA-256 hashes and file contents from the API response
- Does not chunk files, run retrieval, call LLMs, run commands, apply patches,
  or write files

## Context Preview API

Milestone 23 exposes a safe read-only context preview endpoint:

- `POST /repositories/context-preview`
- Accepts `root_path`, `query`, `top_k`, and `max_preview_chars`
- Scans, chunks, and keyword-retrieves deterministic context
- Returns only retrieved chunk previews with relative paths
- Truncates preview text to the requested limit
- Does not call LLMs, plan changes, propose patches, run commands, or write
  files

## Planning Preview API

Milestone 24 exposes a safe read-only deterministic planning endpoint:

- `POST /repositories/plan-preview`
- Accepts `root_path`, `issue`, and `top_k`
- Builds repository context through the existing scan, chunk, and retrieval
  pipeline
- Creates a deterministic `ImplementationPlan`
- Returns plan steps, relevant files, risks, assumptions, confidence, and basic
  context metadata
- Does not call LLMs, propose patches, apply patches, run commands, expose file
  contents, or write files

## Patch Preview API

Milestone 25 exposes a safe deterministic patch proposal preview endpoint:

- `POST /repositories/patch-preview`
- Accepts `root_path`, `issue`, `top_k`, and `max_preview_chars`
- Builds repository context and a deterministic implementation plan
- Reads planned files only through the safe read-only file tool
- Creates a deterministic approval-gated `PatchProposal`
- Returns bounded original/proposed content previews
- Does not call LLMs, apply patches, run validation commands, run shell
  commands, expose hashes, expose unbounded file contents, or write files

## Patch Apply API

Milestone 26 exposes the first approval-gated mutating API endpoint:

- `POST /patches/apply`
- Accepts `root_path`, a reviewed `PatchProposal`, and explicit `approved`
- Applies only through the existing safe patch applier
- Requires `approved=true`
- Requires `proposal.requires_approval=true`
- Returns only changed file summaries
- Does not expose old or new file contents in the response
- Does not run validation commands, call LLMs, run shell commands, generate
  repairs, or start self-correction

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
- Validation failure analyzer for structured failure summaries
- Self-correction orchestrator for bounded approved repair attempts
- LLM repair proposal generator using injected fake/test clients
- Approval-gated repair workflow for generated repair proposals
- Agent run reports for CLI/API/demo/PR summaries
- CLI demo command for printing a sample run report
- Reporting API demo endpoints for JSON and Markdown summaries
- Repository scan summary API endpoint
- Context preview API endpoint with bounded chunk previews
- Planning preview API endpoint with deterministic implementation plans
- Patch proposal preview API endpoint with bounded approval-gated previews
- Approval-gated patch apply API endpoint

Not included yet:

- Embedding retrieval
- Real LLM provider calls
- Vector database
- Autonomous file editing agent
- Automatic repair application without approval
