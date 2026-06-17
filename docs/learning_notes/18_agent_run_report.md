# Learning Note 18: Agent Run Report

## What Was Built

Milestone 19 adds a reporting layer that turns RepoPilot run artifacts into a
structured `AgentRunReport`.

The main function is:

```python
create_agent_run_report(
    issue="Fix login bug",
    plan=plan,
    patch_proposal=proposal,
    validation_result=validation_result,
)
```

It accepts whatever run objects are available and produces a deterministic
summary for CLI output, API responses, demos, or future pull request summaries.

## Why Agent Systems Need Run Reports

Agentic systems can create many intermediate objects:

- context
- plans
- patch proposals
- validation results
- failure analysis
- self-correction attempts
- repair approval requests

Without a reporting layer, each UI or API endpoint would need to understand all
of those objects directly. A run report creates one clean summary of what
happened.

## How Reports Help CLI, API, Demo, And PR Summaries

A report gives callers both structured fields and a human-readable Markdown
summary.

Structured fields are useful for programs:

- status badges
- changed file lists
- validation pass/fail display
- approval state
- failed check names

Markdown is useful for humans:

- terminal output
- demo screens
- pull request descriptions
- review comments

## What Information Is Included

`AgentRunReport` includes:

- `issue`
- `status`
- `summary`
- `planned_files`
- `proposed_files`
- `changed_files`
- `validation_passed`
- `failed_checks`
- `approval_required`
- `repair_proposed`
- `stopped_reason`
- `markdown_summary`

This gives future presentation layers enough information without needing to
inspect every internal model.

## Status Rules

The status is deterministic. Later lifecycle stages win:

1. `self_correction_complete`
2. `self_correction_failed`
3. `repair_ready_for_approval`
4. `validated`
5. `validation_failed`
6. `proposal_ready`
7. `planned`
8. `issue_received`

This means a report can accept several objects from the same run and still
return one clear status.

## Why Reporting Is Separate From Execution

Reporting should observe what already happened. It should not cause new actions.

The reporting layer does not:

- call LLMs
- read files
- write files
- apply patches
- run commands
- start self-correction loops

That makes reports safe to generate at any point.

## Why This Does Not Mutate Anything

The report builder only reads already-created Python objects. It formats lists,
derives booleans, chooses a status, and builds a Markdown string.

No filesystem, command, LLM, patch, or validation tool is called.

## Files Added

### `src/repopilot/reporting/__init__.py`

Exports the public reporting API:

- `AgentRunReport`
- `create_agent_run_report`

### `src/repopilot/reporting/models.py`

Defines the `AgentRunReport` Pydantic model.

This model is the stable contract for future CLI, API, demo, or PR summary
layers.

### `src/repopilot/reporting/run_report.py`

Implements `create_agent_run_report()`.

The function extracts files, validation state, failed checks, approval state,
repair state, stopped reason, and Markdown text from the provided objects.

### `tests/test_run_report.py`

Tests issue-only reports, planned files, proposed files, approval state, changed
files, validation pass/fail status, failed checks, repair approval status,
self-correction status, Markdown output, determinism, and no side effects.

## How To Explain This In An Interview

You can explain this feature like this:

"I added a reporting layer that converts RepoPilot's internal agent artifacts
into a structured run report and Markdown summary. It can summarize plans, patch
proposals, validation results, failure analysis, self-correction results, and
repair approval requests without executing anything. This makes the system ready
for CLI output, API responses, demos, and PR-ready summaries while keeping
reporting separate from action."
