# Learning Note 34: Streamlit Demo UI

## What Was Built

Milestone 37 adds a Streamlit demo frontend:

```text
frontend/streamlit_app.py
```

The UI calls the existing FastAPI endpoints and presents RepoPilot's workflow in
a reviewer-friendly way. It does not add new backend behavior.

## Why Swagger Was Not Enough

Swagger is useful for developers, but it still requires a reviewer to understand
request payloads, endpoint order, and raw JSON responses.

The Streamlit UI gives RepoPilot a guided demo surface. A reviewer can open one
page, enter a repository path and issue once, and click through the main safe
workflow without writing curl commands.

## How The UI Maps To Existing Endpoints

The Streamlit app calls existing safe endpoints:

- `GET /health`
- `GET /demo/workflow`
- `POST /agent/preview`
- `POST /repositories/context-preview`
- `POST /repositories/plan-preview`
- `POST /repositories/patch-preview`

It also displays the demo workflow report returned by `GET /demo/workflow`.

## Tabs In The UI

The UI has eight tabs:

1. Overview
2. Demo Workflow
3. Agent Preview
4. Repository Context
5. Plan Preview
6. Patch Preview
7. Workflow Report
8. Troubleshooting

The first click for a reviewer should be "Run Safe Demo Workflow" because it is
fully in-memory and deterministic.

## Why This Does Not Add Risky Behavior

The UI does not call patch application endpoints. It also does not run validation
commands, generate repairs, start self-correction, or write files.

It is a client for existing read-only preview and reporting endpoints. The Patch
Preview tab clearly says that it does not apply patches.

## OpenRouter Safety

The sidebar includes a `use_llm` checkbox, but it defaults to `false`.

When `use_llm=true`, the FastAPI server must already have
`OPENROUTER_API_KEY` configured in its environment. The UI does not ask the user
to type an API key and does not store secrets in Streamlit state.

If the LLM-backed agent preview fails, the UI shows the backend error and offers
a deterministic fallback button.

## How To Run It

Start FastAPI:

```powershell
uvicorn repopilot.main:app --reload
```

Start Streamlit in another terminal:

```powershell
streamlit run frontend/streamlit_app.py
```

Then open the local Streamlit URL shown in the terminal.

## Files Added Or Updated

### `frontend/streamlit_app.py`

Defines the Streamlit demo UI, sidebar controls, API request helpers, and result
rendering for workflow reports, agent previews, context chunks, plans, and patch
previews.

### `pyproject.toml`

Adds Streamlit as a development/demo dependency.

### `README.md`

Documents how to run the FastAPI backend and Streamlit UI together.

### `CHANGELOG.md`

Records the new demo UI in the Unreleased section.

## How To Explain This In An Interview

You can say:

"After building the backend safety layers, I added a Streamlit demo UI so the
project can be evaluated without Swagger or curl. The UI is intentionally thin:
it calls the existing safe endpoints, renders plans and patch previews clearly,
and never applies patches or runs commands automatically. It defaults to
deterministic mode, while still allowing an OpenRouter-backed preview when the
FastAPI server has the proper environment variables."
