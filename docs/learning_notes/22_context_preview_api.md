# Learning Note 22: Context Preview API

## What Was Built

Milestone 23 adds a safe read-only FastAPI endpoint:

```text
POST /repositories/context-preview
```

The endpoint accepts:

```json
{
  "root_path": "D:/RepoPilot",
  "query": "repository scanner",
  "top_k": 5,
  "max_preview_chars": 500
}
```

It returns repository context metadata and bounded retrieved chunk previews.

## Why A Context Preview API Is Useful

RepoPilot already had a deterministic context builder:

```text
scan -> chunk -> retrieve
```

The API endpoint lets a client preview which parts of a repository look relevant
for a query before any LLM planning or code editing happens.

This is useful for:

- demos
- debugging retrieval
- future frontend context views
- checking whether the system found the right files
- preparing safe inputs for future planning endpoints

## Why This Endpoint Is Read-Only

The endpoint observes repository context. It does not act on the repository.

It does not:

- call LLMs
- create implementation plans
- propose patches
- apply patches
- run commands
- write files

The only file access comes from the existing scanner and chunker behavior.

## How Scan, Chunk, And Retrieve Are Composed

The endpoint delegates to:

```python
build_repository_context(root_path, query, top_k=top_k)
```

That existing function:

1. Scans supported text files.
2. Chunks scanned files.
3. Runs deterministic keyword retrieval.
4. Returns a `RepositoryContext`.

The API layer only maps that context into response schemas.

## Why Previews Are Truncated

Retrieved chunks can contain source text. Returning full chunk text through an
API can expose more content than a preview needs.

The endpoint truncates every preview to `max_preview_chars`.

The request schema limits `max_preview_chars` to a safe range:

```text
50 <= max_preview_chars <= 2000
```

That keeps API responses bounded and demo-friendly.

## Validation Rules

The request schema validates:

- `root_path` must not be blank
- `query` must not be blank
- `top_k` must be between 1 and 20
- `max_preview_chars` must be between 50 and 2000

Scanner and context-building errors are returned as HTTP 400.

## Safety Boundaries

The response contains:

- root name
- scanned file count
- skipped file count
- total chunk count
- retrieved count
- retrieved chunk previews

The response does not include:

- absolute paths
- file hashes
- unbounded file contents
- embeddings
- patch proposals

## How This Prepares Planning Endpoints

Future planning endpoints can use the same context-building pipeline, but this
milestone stops before planning.

The workflow is now visible:

```text
scan summary API -> context preview API -> future planning API
```

That gives RepoPilot a gradual API surface where each step remains testable and
safe.

## Files Added Or Updated

### `src/repopilot/api/context.py`

Defines `POST /repositories/context-preview`.

The route calls `build_repository_context()` and maps the result into bounded
chunk previews.

### `src/repopilot/schemas/context.py`

Defines:

- `ContextPreviewRequest`
- `ContextChunkPreview`
- `ContextPreviewResponse`

### `src/repopilot/main.py`

Includes the context router in the FastAPI app.

### `tests/test_context_preview_api.py`

Tests success, summary fields, chunk preview fields, truncation, relative paths,
request validation, missing roots, deterministic output, omitted hashes, and no
LLM, command, patch, or write side effects.

### `README.md`

Documents the endpoint and an example request body.

## How To Explain This In An Interview

You can explain this feature like this:

"I added a safe context preview API that exposes RepoPilot's deterministic
scan-chunk-retrieve pipeline. Given a repository path and query, it returns
metadata plus bounded previews of the most relevant chunks. The endpoint
validates inputs, keeps paths relative, truncates previews, and does not call
LLMs, plan changes, run commands, apply patches, or write files. It prepares the
backend for future planning endpoints while keeping the context step
observable and safe."
