# 00 - Project Skeleton

This note explains the first RepoPilot foundation. The goal is not to build the
agent yet. The goal is to create a small, understandable backend shape that can
grow safely.

## Created Files

### `.gitignore`

Tells Git to ignore local Python artifacts such as virtual environments, cache
folders, package metadata, and `.env` files.

What to learn:

- Generated files should not be committed.
- `.env` belongs on your machine, not in source control.
- Ignoring common local files keeps diffs focused on real project changes.

### `.env.example`

Shows the environment variables the app currently understands.

What to learn:

- Example env files document configuration without exposing secrets.
- Future teammates can copy this file to `.env` and adjust local values.
- Even when there are no secrets yet, it is useful to establish the pattern.
- `OPENAI_API_KEY` is left blank for later LLM work and is not used by this
  skeleton.

### `AGENTS.md`

Existing project guidance for how Codex should work in this repository.

What to learn:

- Agent projects benefit from explicit working rules.
- The file defines scope control, testing expectations, documentation habits, and
  the "done means" checklist.

### `docs/project_brief.md`

Existing product brief for the RepoPilot portfolio project.

What to learn:

- The brief keeps the long-term agentic AI goal visible.
- It separates the final vision from the first milestone, which prevents the
  initial skeleton from becoming too large.

### `pyproject.toml`

Defines the Python project metadata, package discovery, runtime dependencies,
development dependencies, pytest settings, and Ruff settings.

What to learn:

- Modern Python projects can use `pyproject.toml` as the central configuration
  file.
- The `src` layout keeps import behavior honest because the package must be
  installed or included in the test path.
- Runtime dependencies are separate from development dependencies.
- Ruff can handle fast linting and formatting from one config file.

### `README.md`

Documents what RepoPilot is, what this first milestone includes, and exactly how
to set up, run, test, and lint the project.

What to learn:

- A README should make the project runnable by someone who has never seen it.
- It should clearly separate current scope from future ambition.
- Early documentation prevents the project from becoming mysterious as it grows.

### `src/repopilot/__init__.py`

Marks `repopilot` as a Python package and exposes the package version.

What to learn:

- Packages need an import root.
- Keeping `__version__` in one place lets the API and project metadata stay easy
  to reason about.

### `src/repopilot/main.py`

Creates the FastAPI application through a `create_app()` function and exposes an
`app` object for Uvicorn.

What to learn:

- An app factory makes startup configuration easier to test and extend.
- `uvicorn repopilot.main:app --reload` works because this file exports `app`.
- Routers keep endpoint code out of the main application file.

### `src/repopilot/api/__init__.py`

Marks the API folder as a package.

What to learn:

- API routes live together under one namespace.
- This folder will later hold routes for repository ingestion, planning, edits,
  and check runs.

### `src/repopilot/api/health.py`

Defines the `/health` route.

What to learn:

- A health endpoint is a tiny but useful production habit.
- It lets tests, deployment platforms, and humans confirm that the API process is
  responding.
- The route returns a Pydantic response model instead of a loose dictionary.

### `src/repopilot/core/__init__.py`

Marks the core folder as a package.

What to learn:

- Core modules hold cross-cutting application concerns.
- Configuration belongs here because many future modules will need it.

### `src/repopilot/core/config.py`

Defines typed application settings with `pydantic-settings`.

What to learn:

- Settings should come from environment variables, not hardcoded secrets.
- The `REPOPILOT_` prefix keeps environment variables organized.
- `@lru_cache` avoids rebuilding settings on every request.

Example environment variables:

```text
REPOPILOT_APP_NAME=RepoPilot
REPOPILOT_ENVIRONMENT=development
REPOPILOT_LOG_LEVEL=info
```

### `src/repopilot/schemas/__init__.py`

Marks the schemas folder as a package.

What to learn:

- Schemas are the contract between the API and its callers.
- Keeping schemas separate makes future request and response models easier to
  find.

### `src/repopilot/schemas/health.py`

Defines the `HealthResponse` Pydantic model.

What to learn:

- Pydantic models validate and document API payload shapes.
- A typed response model gives FastAPI enough information to generate accurate
  OpenAPI docs.

### `tests/__init__.py`

Marks the tests folder as a package.

What to learn:

- Test files live outside application code.
- Keeping tests separate makes it easier to grow confidence without mixing
  production and test-only code.

### `tests/test_health.py`

Tests the `/health` endpoint with FastAPI's `TestClient`.

What to learn:

- Endpoint tests can run without starting a real web server.
- A small test proves the app imports, routes are registered, and the response
  contract is stable.

## Why This Shape Works

RepoPilot will eventually need modules for ingestion, indexing, retrieval,
planning, editing, check execution, and PR summaries. This skeleton gives those
future pieces clear places to live without implementing them too early.

The current architecture keeps three boundaries visible:

- `api`: HTTP routes and request handling.
- `core`: shared app concerns such as settings.
- `schemas`: typed API contracts.

That is enough structure for a real backend, but still small enough to explain
in one sitting.
