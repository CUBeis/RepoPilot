# 04 - Repository Context Builder

Milestone 5 adds the repository context builder. It composes the deterministic
scanner, code chunker, and keyword retriever into one pipeline:

```text
scan repository -> chunk scanned files -> retrieve relevant chunks for a query
```

This is still not an agent. It is the context-preparation layer that future
agents will use before planning or editing code.

## What The Context Builder Does

The builder accepts a repository root path and a natural language query. It:

1. Scans the repository.
2. Chunks every scanned file.
3. Runs keyword retrieval over all chunks.
4. Returns a structured `RepositoryContext`.

The context includes:

- Repository root name
- Scanned file count
- Total scanned file size
- Skipped file count
- Total chunks created
- Retrieved chunks for the query

## Why Composition Matters

Each earlier milestone solved one focused problem:

- The scanner finds supported text files.
- The chunker turns files into smaller text units.
- The retriever ranks chunks for a query.

The context builder proves those pieces work together without mixing their
responsibilities. This keeps the architecture easier to test and explain.

## How The Pieces Connect

The builder calls `scan_repository()` first. That returns `ScannedFile` metadata.

Then it calls `chunk_file()` for each scanned file. That produces `CodeChunk`
objects with path, language, line range, text, and hash.

Finally, it calls `retrieve_keyword_chunks()` with the chunk list and user query.
That returns ranked `RetrievedChunk` objects with scores and matched terms.

## Why This Is Still Not An Agent

An agent chooses actions, plans work, calls tools, observes results, and loops
until a task is complete.

The context builder does none of that. It does not decide what code to change,
write files, run tests, call an LLM, or self-correct. It only prepares relevant
context deterministically.

That separation is important because future agents need reliable inputs.

## How This Prepares For LLM Planning

Before an LLM can plan a code change, RepoPilot needs to gather the right context.
The context builder gives a future planner:

- Which files were scanned
- How many chunks exist
- Which chunks matched the query
- Why chunks matched through `matched_terms`
- Exact relative paths and line ranges

This creates a clean handoff between deterministic retrieval and future LLM
reasoning.

## What Deterministic Context Means

Deterministic context means the same repository and query produce the same
structured result every time.

This matters because:

- Tests can verify behavior.
- Retrieval can be debugged.
- Future evaluations can compare runs fairly.
- Agents can be easier to observe and trust.

## Files Involved

### `src/repopilot/context/__init__.py`

Exports the public context-building API.

What to learn:

- `build_repository_context` is the main entry point for this milestone.
- The package also exposes `RepositoryContext` and `ContextBuildError`.

### `src/repopilot/context/models.py`

Defines the `RepositoryContext` Pydantic model.

What to learn:

- The context result is a typed contract between retrieval and future planning.
- Summary fields make the pipeline observable.

### `src/repopilot/context/builder.py`

Composes scanner, chunker, and retriever.

What to learn:

- Composition layers should stay thin.
- Existing modules should be reused instead of duplicated.
- Chunking errors are wrapped with file-path context so failures are clear.

### `tests/test_context_builder.py`

Tests the full deterministic pipeline with temporary repositories.

What to learn:

- Integration-style unit tests prove modules work together.
- The tests verify scan summaries, chunk counts, retrieval, `top_k`, invalid
  paths, nested files, and deterministic results.

## Interview Explanation

You can explain this feature like this:

"After building scanner, chunker, and keyword retrieval primitives, I composed
them into a repository context builder. Given a repo path and query, it scans
supported files, chunks them deterministically, retrieves relevant chunks, and
returns a typed context object with scan summary, chunk count, and ranked
results. It is not an agent yet; it is the reliable context-preparation pipeline
that a future planning agent will consume."
