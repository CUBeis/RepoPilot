# 01 - Repository Scanner

Milestone 2 adds a deterministic repository scanner. It accepts a local
repository root, validates it, walks the file tree, skips noisy or unsafe files,
and returns structured metadata about supported text files.

This is the first real step before codebase RAG. Before RepoPilot can chunk
files, create embeddings, retrieve context, or ask an agent to plan edits, it
needs a reliable inventory of the repository.

## What Was Built

The scanner returns metadata for each supported text file:

- Relative path
- Detected language from file extension
- Extension
- File size in bytes
- Line count
- SHA-256 content hash

It also returns a scan summary:

- Repository root name
- Number of scanned files
- Total size of scanned files
- Number of skipped files
- List of scanned file metadata

The scanner does not read or return full file contents. It does not chunk files,
call an LLM, create embeddings, or use a vector database.

## Files Involved

### `src/repopilot/repository/__init__.py`

Exports the public repository scanning API.

What to learn:

- Package `__init__` files can define the small public surface of a module.
- Other code can import `scan_repository` without knowing every internal file.

### `src/repopilot/repository/models.py`

Defines the Pydantic models `ScannedFile` and `RepositoryScanResult`.

What to learn:

- Scanner output should be structured, typed, and easy to validate.
- Pydantic models make metadata predictable for later API, retrieval, and agent
  layers.

### `src/repopilot/repository/filters.py`

Defines ignored directories, supported text extensions, language detection, and
small helper functions.

What to learn:

- Filtering rules should live separately from the scanner walk logic.
- Extension-based language detection is simple but deterministic.
- The scanner can grow later without mixing every rule into one large function.

### `src/repopilot/repository/scanner.py`

Validates the repository root, recursively walks files, applies filters, skips
binary and large files, computes metadata, and returns `RepositoryScanResult`.

What to learn:

- Deterministic filesystem logic should be separate from future LLM logic.
- Good scanners fail clearly for invalid input.
- Returning relative paths avoids leaking machine-specific absolute paths.

### `tests/test_repository_scanner.py`

Tests the scanner with temporary directories.

What to learn:

- Temporary directory tests are ideal for filesystem behavior.
- Each scanner rule gets a focused test.
- The tests prove the scanner works without depending on a real external repo.

## Why Ignore Common Folders

Folders such as `.git`, `.venv`, `node_modules`, `__pycache__`, `dist`, and
`build` are usually generated, huge, duplicated, or not useful for source-code
reasoning.

Ignoring them matters because:

- Scans stay fast.
- Results stay focused on source files.
- Future embeddings avoid noisy dependency and build output content.
- RepoPilot avoids wasting context budget on files it should not reason over.

## What The Metadata Means

`path` is the file path relative to the scanned root. This makes results portable
across machines.

`language` is a basic label inferred from the extension. It is good enough for
early routing and can be improved later.

`extension` keeps the raw normalized file type visible.

`size_bytes` helps enforce scan limits and understand repository size.

`line_count` helps later chunking choose sensible boundaries.

`sha256` is a stable fingerprint of file contents.

## Why SHA-256 Is Useful

SHA-256 lets RepoPilot detect when a file changed without storing the full
content in every metadata record. Later milestones can use hashes to:

- Avoid re-indexing unchanged files.
- Compare scan snapshots.
- Cache chunks and embeddings safely.
- Explain which files changed between runs.

## Why Skip Binary And Large Files

Binary files are not useful for text chunking or embeddings in this early
scanner. Large files can slow scans, consume memory, and create oversized future
chunks.

Skipping them keeps Milestone 2 safe and predictable. Later, RepoPilot can add
special handling for images, notebooks, generated files, or large documents.

## How This Connects Later

This scanner becomes the input to future milestones:

1. Chunking reads selected scanned files and splits source text into chunks.
2. Embeddings turn chunks into vectors.
3. Retrieval finds relevant chunks for a coding task.
4. Planning uses retrieved context to propose safe changes.
5. Agents use scan metadata to decide which files to inspect or edit.
6. Test and review loops can compare file hashes before and after changes.

## Interview Explanation

You can explain this feature like this:

"I started RepoPilot with a deterministic repository scanner before adding any
LLM behavior. It validates a local repo path, ignores noisy generated folders,
scans supported text files, skips binary and oversized files, and returns typed
metadata including relative path, language, size, line count, and SHA-256 hash.
This creates a reliable inventory of the codebase, which later powers chunking,
embeddings, retrieval, planning, and agentic code editing."
