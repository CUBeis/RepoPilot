# RepoPilot Project Brief

## One-Line Description

RepoPilot is an Agentic AI Software Engineer that can understand a codebase, plan code changes, safely modify files, run tests, fix failures, and generate PR-ready summaries.

## Problem

Most AI coding demos are simple chat interfaces. They can explain code, but they do not act like real software engineering agents. Real engineering work requires reading many files, understanding dependencies, planning safe changes, editing code, validating changes with tests, and explaining the final result.

RepoPilot is designed to demonstrate those production-level agentic abilities.

## Target User

A developer who wants an AI assistant to help with repository-level coding tasks such as:

* Fixing bugs
* Adding small features
* Writing tests
* Refactoring code
* Explaining codebase structure
* Preparing pull request summaries

## Core Workflow

1. User provides a local repository or GitHub repository.
2. RepoPilot scans and indexes the codebase.
3. User provides an issue or task.
4. The planner agent creates an implementation plan.
5. The retriever finds relevant files and code chunks.
6. The implementation agent edits files safely.
7. The test runner executes tests and lint checks.
8. If tests fail, the agent reads the error and tries to fix the issue.
9. The reviewer agent summarizes the final changes.
10. The system outputs a PR-ready report.

## Main Concepts Demonstrated

* Agentic AI
* Tool calling
* Codebase RAG
* Embeddings and vector search
* Agent state management
* Planning and execution
* Reflection and self-correction
* Human-in-the-loop approval
* Test-driven validation
* Observability and logs
* Evaluation benchmarks

## First Milestone

Create a clean Python project skeleton with:

* FastAPI backend
* Pydantic schemas
* Basic health endpoint
* Modular folder structure
* Pytest setup
* Ruff setup
* Documentation structure
* Learning notes

## Final Portfolio Goal

The finished project should be strong enough to place at the top of my CV as an Agentic AI Engineering project.
