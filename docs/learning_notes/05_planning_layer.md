# 05 - Planning Layer

Milestone 6 adds RepoPilot's first planning layer. It accepts a user issue and a
`RepositoryContext`, builds a clear planning prompt, and returns a structured
`ImplementationPlan`.

This is the first step toward agentic behavior, but it still does not edit files,
run tests, call tools, or use a real LLM API.

## What Planning Means

Planning means turning a user request and repository context into an ordered
proposal for what should happen next.

In RepoPilot, the plan includes:

- Objective
- Relevant files
- Ordered steps
- Risks
- Assumptions
- Confidence score

## Why Planning Comes Before Acting

Real software engineering work should not jump straight from a user issue to
file edits. A planning step helps the system decide:

- Which files appear relevant
- What needs inspection
- What risks exist
- What assumptions are being made
- Whether there is enough context to proceed

This makes future edits safer and easier to review.

## Why This Milestone Does Not Edit Files Yet

Editing code is a higher-risk action. Before RepoPilot can safely modify files,
it needs a structured plan that humans or future approval systems can inspect.

This milestone deliberately stops at planning. It does not write files, run
tests, call shell tools, or self-correct from failures.

## From Repository Context To Implementation Plan

The `RepositoryContext` contains scan metadata and retrieved chunks. The planner
uses that context to:

1. Set the objective from the issue.
2. Collect relevant files from retrieved chunk paths.
3. Create ordered steps based on retrieved files and matched terms.
4. Add risks and assumptions.
5. Assign confidence.

If retrieved chunks exist, confidence is higher. If no chunks were retrieved, the
planner returns a low-confidence plan and assumes more context is needed.

## What Structured Output Means

Structured output means the plan is not a loose paragraph. It is a typed
`ImplementationPlan` object with predictable fields.

This matters because later agent layers can consume the plan safely. For example,
a future executor can read `steps`, inspect `target_files`, and require human
approval before editing anything.

## Why Deterministic Planning First

Deterministic planning is useful before adding a real LLM because it is:

- Easy to test
- Easy to debug
- Stable across runs
- Clear enough for interviews
- A baseline for future LLM-generated plans

Later, RepoPilot can compare deterministic plans with LLM plans and evaluate
whether the LLM improves quality.

## How This Connects Later

The planning layer will eventually connect to:

- LLM prompt calls
- Human approval checkpoints
- File editing tools
- Test execution tools
- Self-correction loops
- Pull request summaries

The current prompt builder already formats the issue and retrieved chunks in a
way a future LLM planner can consume.

## Files Involved

### `src/repopilot/planning/__init__.py`

Exports the public planning API.

What to learn:

- The package exposes the models, prompt builder, planner, and error type.
- A small public surface makes the next milestone easier to build.

### `src/repopilot/planning/models.py`

Defines `PlanStep` and `ImplementationPlan`.

What to learn:

- Plans should be structured and typed.
- Confidence is constrained between 0 and 1.
- Each step has an order and target files.

### `src/repopilot/planning/prompt.py`

Builds a deterministic planning prompt from an issue and repository context.

What to learn:

- Prompt construction can be tested before real LLM calls exist.
- Retrieved chunks can be formatted with paths, line ranges, scores, matched
  terms, and text.

### `src/repopilot/planning/planner.py`

Creates a deterministic `ImplementationPlan`.

What to learn:

- The deterministic planner is a placeholder for future LLM-backed planning.
- It still returns useful structured output.
- Empty or weak context should lower confidence.

### `tests/test_planning_layer.py`

Tests prompt building and deterministic planning.

What to learn:

- Planning can be tested without external APIs.
- Tests verify prompt content, relevant files, ordered steps, errors, low
  confidence, determinism, and confidence bounds.

## Interview Explanation

You can explain this feature like this:

"After building deterministic scanning, chunking, retrieval, and context
building, I added a planning layer. It accepts a user issue and retrieved
repository context, builds a planning prompt, and returns a typed implementation
plan with objective, relevant files, ordered steps, risks, assumptions, and
confidence. It does not edit files or call an LLM yet, which keeps the system
safe and testable before adding real agent execution."
