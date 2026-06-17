# 14 - Validation Failure Analyzer

Milestone 15 adds a validation failure analyzer. It accepts a
`PatchValidationResult` and returns a structured `FailureAnalysis`.

This milestone does not rerun commands, apply patches, call LLMs, create repair
patches, add API endpoints, or self-correct.

## What Was Built

The main function is:

```python
analyze_validation_result(result)
```

It returns:

- Whether validation passed
- Number of failed checks
- Structured summaries of failed checks
- A human-readable summary
- Whether future self-correction is needed

Each failed check summary includes:

- Check name
- Command
- Return code
- Timeout flag
- Stdout excerpt
- Stderr excerpt

## Why Failure Analysis Comes Before Self-Correction

Self-correction should not jump straight from raw command output to new edits.
First, RepoPilot needs to understand what failed in a structured way.

Failure analysis creates the observation layer:

```text
validation result -> failure analysis -> future repair planning
```

This makes later repair behavior easier to test, inspect, and constrain.

## What Structured Failure Summaries Are

Raw terminal output can be long, noisy, and hard for later components to consume.
A structured failure summary turns command results into predictable fields:

- Which check failed
- Which command was run
- Whether it timed out
- What return code it produced
- Relevant stdout and stderr excerpts

This creates a stable input for future LLM-backed diagnosis or deterministic
failure routing.

## How Command Output Becomes Agent-Readable Context

The analyzer copies stdout and stderr excerpts into `FailedCheckSummary`.

By default, each excerpt is limited to 1000 characters. This keeps future prompts
or logs from being overwhelmed by huge test output while still preserving useful
failure context.

The max excerpt length is configurable for tests and future workflows.

## Timeout Handling

Timeouts are called out clearly in the summary. A timed-out test run is
different from a failing test assertion, so future diagnosis should be able to
treat it differently.

For example, a timeout may suggest:

- A hanging test
- An infinite loop
- A command that needs a longer timeout
- A process waiting for input

The analyzer only reports that distinction. It does not fix it.

## Why This Still Does Not Fix Anything

This milestone is intentionally read-only with respect to execution and files.

It does not:

- Run commands
- Apply patches
- Edit files
- Call an LLM
- Generate a repair plan
- Retry validation

Those behaviors belong to later self-correction milestones.

## Files Involved

### `src/repopilot/validation/models.py`

Adds `FailedCheckSummary` and `FailureAnalysis`.

What to learn:

- Agent observations should be typed and compact.
- Failure state should be explicit enough for later repair logic.

### `src/repopilot/validation/failure_analysis.py`

Implements `analyze_validation_result()`.

What to learn:

- Failure analysis can be deterministic before adding LLM reasoning.
- Command output should be excerpted before becoming future agent context.
- Timeouts and return-code failures should be represented differently.

### `tests/test_failure_analysis.py`

Tests successful validation analysis, failed checks, timeouts, excerpt
truncation, failed check counts, self-correction flags, determinism, no command
execution, and no file mutation.

What to learn:

- Analysis layers should prove they only analyze.
- Negative tests protect the boundary before future agent loops exist.

## Interview Explanation

You can explain this feature like this:

"I added a validation failure analyzer that converts a PatchValidationResult into
a structured FailureAnalysis. It detects failed checks, records command names,
return codes, timeout status, and stdout/stderr excerpts, and marks whether
self-correction will be needed later. It deliberately does not rerun commands,
call an LLM, edit files, or create repair patches. It is the observation layer
that future self-correction can consume."
