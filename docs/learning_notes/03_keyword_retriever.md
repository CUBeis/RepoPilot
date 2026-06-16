# 03 - Deterministic Keyword Search Retriever

Milestone 4 adds a deterministic keyword retriever. It accepts a list of
`CodeChunk` objects and a natural language query, then returns the highest
scoring chunks using explainable keyword overlap.

The retriever does not call an LLM, create embeddings, use a vector database,
rerank results, or expose an API endpoint.

## What Retrieval Means

Retrieval means selecting the most relevant pieces of context for a user query.
In RepoPilot, the retrieved context will eventually help the system understand
which files and chunks matter for a coding task.

The retriever returns:

- The matching `CodeChunk`
- A numeric score
- The query terms that matched the chunk

## Why Retrieval Comes Before LLM Reasoning

LLMs work better when they receive focused context instead of an entire
repository. Retrieval is the step that chooses that context.

Before adding agents, planning, or code editing, RepoPilot needs a deterministic
way to answer: "Which chunks look relevant to this task?"

## Why Keyword Retrieval Before Embeddings

Keyword retrieval is useful as a first implementation because it is:

- Simple
- Fast
- Deterministic
- Easy to test
- Easy to explain

It also creates a baseline that future embedding retrieval can be compared
against.

## How Scoring Works

The retriever tokenizes the query, chunk path, and chunk text. It lowercases text
and ignores simple punctuation.

Each unique query term can match:

- The chunk path
- The chunk text
- Both

By default:

- Path matches are worth `2.0`
- Text matches are worth `1.0`

For example, if the query is `auth login`:

- A chunk at `auth/routes.py` gets extra score for matching `auth` in the path.
- A chunk containing `login` in its text gets score for the text match.
- A chunk matching both path and text ranks higher.

## Why Path Matches Have Extra Weight

File paths often contain strong signals such as feature names, domains, and
module boundaries. A query about authentication is likely to care about files
under `auth/`, even if the exact query words appear only a few times in the
text.

Path weighting helps RepoPilot prefer chunks whose location is semantically
important.

## What `matched_terms` Means

`matched_terms` lists the query tokens that matched either the path or the text.

This is useful because it makes retrieval explainable. Later, RepoPilot can show
why a chunk was selected before an agent uses it for planning.

## Deterministic Ordering

Results are sorted by score descending. Ties are broken by path, chunk index,
start line, and end line.

That means the same chunks and query produce the same result order every time,
even when two chunks have equal scores.

## Limitations

Keyword retrieval cannot understand synonyms or deeper meaning. A query for
`sign in` may not match code that uses `login` unless both terms appear in the
text or path.

It also does not understand syntax, imports, call graphs, or semantic similarity.
Those limitations are acceptable for this milestone because the goal is a
transparent baseline.

## How This Compares With Embeddings Later

Embedding retrieval will later represent chunks as vectors and find semantic
similarity, even when exact words differ.

Keyword retrieval will still be useful because:

- It is cheap and deterministic.
- It can be combined with vector search.
- It provides a baseline for evaluation.
- It catches exact symbol, filename, and keyword matches very well.

## Interview Explanation

You can explain this feature like this:

"After scanning and chunking repositories, I added a deterministic keyword
retriever. It tokenizes a user query and code chunks, scores matches in both file
paths and chunk text, weights path matches higher, and returns ranked chunks with
matched terms. This gives RepoPilot an explainable retrieval baseline before
adding embeddings or LLM agents."
