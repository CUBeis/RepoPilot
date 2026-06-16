# AGENTS.md

## Project Name

RepoPilot — Agentic AI Software Engineer

## Project Goal

Build a production-grade Agentic AI portfolio project that can analyze a codebase, plan code changes, safely edit files, run tests, self-correct from failures, and generate PR-ready summaries.

This project must not be a toy chatbot. It should demonstrate real agentic AI engineering concepts:

* Tool calling
* Codebase RAG
* Agent state
* Planning
* Self-correction loops
* Human approval checkpoints
* Testing and evaluation
* Observability and traceable execution

## Working Rules for Codex

* Do not build large features in one step.
* Before coding, inspect the repository and write a short implementation plan.
* Explain design choices before implementing.
* Keep code modular and readable.
* Prefer simple, testable architecture over clever abstractions.
* Do not hardcode API keys or secrets.
* Use environment variables for configuration.
* Every feature must include or update tests.
* Every feature must update `docs/learning_notes/`.
* After implementation, explain:

  * What changed
  * Why the design was chosen
  * How to run it
  * How to test it
  * What concepts I should learn from it

## Tech Stack

* Python 3.11+
* FastAPI backend
* Pydantic for schemas
* Pytest for tests
* Ruff for linting
* Docker support later
* Vector database later: Chroma or Qdrant
* LLM orchestration later: LangGraph or OpenAI Agents SDK

## Code Quality

* Use type hints.
* Use clear module names.
* Avoid huge files.
* Avoid hidden side effects.
* Keep business logic separate from API routes.
* Add docstrings for important classes and functions.
* Add meaningful error handling.

## Testing Rules

* Add tests for core logic.
* Do not claim tests pass unless they were actually run.
* If tests fail, explain the failure and fix it.
* Prefer small unit tests first.

## Documentation Rules

For every feature, create or update a learning note under:

`docs/learning_notes/`

Each learning note should explain:

* What was built
* Why it exists
* How it works
* What files are involved
* What Agentic AI or LLM concept it teaches
* How I can explain it in an interview

## Done Means

A task is done only when:

* The code works
* Tests are added or updated
* Documentation is updated
* The implementation is explained clearly
* The next recommended step is provided
