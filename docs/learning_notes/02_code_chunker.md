# 02 - Deterministic Code Chunker

Milestone 3 adds a deterministic code chunker. It takes a repository root and a
`ScannedFile`, reads the file safely, and splits the text into line-based chunks
with overlap.

The chunker does not call an LLM, create embeddings, use a vector database,
parse ASTs, or expose an API endpoint. It prepares clean units of text for later
RAG and retrieval milestones.

## What Chunking Means

Chunking means splitting a larger file into smaller text sections. Instead of
sending an entire repository file into a future retrieval system, RepoPilot will
store and search smaller chunks.

Each chunk includes:

- Relative file path
- Language
- Chunk index
- Start line
- End line
- Chunk text
- SHA-256 hash of the chunk text

## Why LLMs Need Chunking Before RAG

RAG systems work best when they retrieve focused context. A whole file can be too
large, noisy, or unrelated to the exact issue a user asks about.

Chunking helps because:

- Retrieval can find the most relevant sections instead of whole files.
- Embeddings can represent smaller, more specific units of meaning.
- Future prompts can include enough context without wasting token budget.
- Agents can cite exact file paths and line ranges when planning edits.

## Why Line-Based Chunking First

Line-based chunking is a good first implementation because it is simple,
deterministic, and easy to test.

It does not require language parsers or AST logic. That makes it a strong
foundation before adding smarter semantic chunking later.

## What Overlap Means

Overlap means repeating a few lines from the end of one chunk at the beginning of
the next chunk.

For example, with `max_lines_per_chunk=5` and `overlap_lines=2`:

- Chunk 0 covers lines 1-5
- Chunk 1 covers lines 4-8
- Chunk 2 covers lines 7-11

Overlap helps preserve context that sits near chunk boundaries. Without overlap,
a function signature, comment, or important setup line could be separated from
the code that depends on it.

The chunker requires `overlap_lines` to be smaller than `max_lines_per_chunk` so
each chunk still moves forward.

## Files Involved

### `src/repopilot/chunking/__init__.py`

Exports the public chunking API.

What to learn:

- The package exposes `chunk_file`, `CodeChunk`, and `CodeChunkingError`.
- Keeping exports small makes the module easier to use later.

### `src/repopilot/chunking/models.py`

Defines the `CodeChunk` Pydantic model.

What to learn:

- Chunk metadata should be structured and typed before it reaches embeddings or
  retrieval.
- The model records path, language, chunk index, line range, text, and hash.

### `src/repopilot/chunking/chunker.py`

Implements deterministic line-based chunking.

What to learn:

- The chunker validates the root directory.
- It prevents scanned paths from escaping the repository root.
- It skips empty files.
- It reads text as UTF-8.
- It creates stable chunk hashes from chunk text.

### `tests/test_code_chunker.py`

Tests the chunker using temporary files.

What to learn:

- Temporary files make chunking behavior easy to test.
- Tests cover overlap, line ranges, hashes, empty files, invalid config, path
  safety, relative paths, and determinism.

## How Chunk Metadata Connects Later

Future milestones can use `CodeChunk` objects as the input to:

1. Embedding generation
2. Vector storage
3. Retrieval for a coding task
4. Planner context selection
5. Agent edit proposals
6. PR summaries that cite exact line ranges

The chunk hash also helps with caching. If a chunk hash has not changed, RepoPilot
can later avoid recomputing its embedding.

## Limitations

Line-based chunking is intentionally simple. It can split in the middle of a
function, class, Markdown section, or SQL query. It does not understand syntax or
semantic boundaries yet.

That is acceptable for this milestone because the goal is to build a reliable
baseline first. Later improvements can add language-aware or AST-based chunking.

## Interview Explanation

You can explain this feature like this:

"After building a repository scanner, I added deterministic line-based chunking.
The chunker takes a scanned file, validates that it stays inside the repository,
reads it as text, and creates overlapping chunks with path, language, line range,
text, and SHA-256 hash. I kept it separate from LLM and embedding logic so the
retrieval pipeline has a reliable, testable foundation."
