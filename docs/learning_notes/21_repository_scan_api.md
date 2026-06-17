# Learning Note 21: Repository Scan Summary API

## What Was Built

Milestone 22 adds a safe read-only FastAPI endpoint:

```text
POST /repositories/scan-summary
```

The endpoint accepts:

```json
{
  "root_path": "D:/RepoPilot"
}
```

It returns repository scan summary metadata:

- root name
- scanned file count
- total scanned size in bytes
- skipped file count
- scanned file summaries

## Why A Repository Scan API Is Useful

RepoPilot already had a deterministic scanner as a Python function. An API
endpoint makes that capability available to future clients such as:

- a frontend
- CLI wrappers
- demos
- workflow orchestration services
- evaluation tools

This is the first real repository-aware API surface.

## Why This Endpoint Is Read-Only

Scanning should only observe repository metadata. This endpoint does not:

- write files
- apply patches
- run commands
- call LLMs
- chunk files
- run retrieval
- generate plans

That makes it safe to expose before adding higher-risk workflow endpoints.

## Why It Only Returns Summaries

The API response intentionally omits:

- full file contents
- chunk text
- embeddings
- patch data
- SHA-256 hashes

The endpoint returns only the metadata needed to understand what the scanner
found. File paths are relative to the repository root, which avoids exposing
machine-specific absolute paths in normal scan results.

## How It Reuses The Scanner

The route delegates to the existing deterministic scanner:

```python
scan_repository(root_path)
```

It then maps `RepositoryScanResult` into API response schemas. The API layer does
not reimplement scanning rules.

## Safety Boundaries

The request schema validates that `root_path` is not blank.

The scanner still handles:

- missing paths
- paths that are files instead of directories
- ignored directories
- unsupported files
- binary files
- oversized files

Scanner validation errors become HTTP 400 responses.

## How This Prepares Future Context-Building Endpoints

Future endpoints can build on this pattern:

```text
request schema -> safe deterministic layer -> response schema
```

Next API milestones can expose context building, retrieval, planning, or approval
requests while keeping each step bounded and testable.

## Files Added Or Updated

### `src/repopilot/api/repositories.py`

Defines the repository API router and `POST /repositories/scan-summary`.

The route catches `RepositoryScanError` and returns HTTP 400.

### `src/repopilot/schemas/repositories.py`

Defines:

- `RepositoryScanSummaryRequest`
- `ScannedFileSummary`
- `RepositoryScanSummaryResponse`

The response model intentionally excludes `sha256` and file contents.

### `src/repopilot/main.py`

Includes the repository router in the FastAPI app.

### `tests/test_repository_scan_api.py`

Tests successful scans, summary fields, relative paths, omitted hashes, invalid
roots, deterministic output, and no LLM, command, patch, or write side effects.

### `README.md`

Documents the endpoint and an example request body.

## How To Explain This In An Interview

You can explain this feature like this:

"I exposed RepoPilot's deterministic repository scanner through a safe FastAPI
endpoint. The endpoint accepts a local repository path, delegates to the existing
scanner, and returns a typed summary with relative file paths, language,
extension, size, and line counts. It deliberately omits file contents and hashes
from the API response, maps scanner validation errors to HTTP 400, and does not
chunk, retrieve, call LLMs, run commands, or write files. This creates a safe
repository-aware API foundation for future context-building endpoints."
