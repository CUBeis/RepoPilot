# 13 - Patch Validation Pipeline

Milestone 14 adds a validation pipeline that composes two existing safe tools:

```text
safe patch applier -> safe command runner
```

The new pipeline applies an approved `PatchProposal`, then runs allowlisted
validation commands such as `pytest` and `ruff check .`.

This milestone does not call LLMs, add API endpoints, run arbitrary commands, or
self-correct from failures.

## What Was Built

The main function is:

```python
apply_and_validate_patch(
    root_path,
    proposal,
    approved=True,
    validation_commands=None,
    timeout_seconds=30,
)
```

It returns a `PatchValidationResult` with:

- `apply_result`
- `checks`
- Overall `passed` flag

Each `ValidationCheck` includes:

- Name
- Command
- `CommandResult`
- Whether the check passed

## Apply Then Validate

The pipeline always applies the patch first by calling `apply_patch_proposal()`.

Only if patch application succeeds does it run validation commands. This matters
because running tests before a patch applies would not validate the proposed
change.

If patch application fails, the error is propagated and no commands are run.

## Why Validation Is Separate From Self-Correction

Validation observes whether a patch works. Self-correction decides what to do
when validation fails.

This milestone only observes:

- Did the command return code equal `0`?
- Did the command avoid timing out?
- What stdout and stderr were produced?

It does not:

- Analyze failures with an LLM
- Generate a repair patch
- Reapply changes
- Retry commands
- Loop until success

Keeping validation separate makes the system easier to test and safer to extend.

## Why Command Allowlists Still Matter

The validation pipeline passes the requested validation commands as the
allowlist to `run_command()`.

That means the pipeline can run only the commands it was explicitly asked to
run. Even though this layer composes tools, it does not weaken the command
runner's safety boundary.

The default validation commands are:

```python
["pytest"]
["ruff", "check", "."]
```

## How This Prepares For Failure Analysis

The pipeline returns structured command results with stdout, stderr, return
code, and timeout status. A future failure analysis layer can consume that data
and decide what failed.

Later milestones can add:

1. Failure summarization
2. LLM-backed diagnosis
3. Repair planning
4. New patch proposals
5. Revalidation loops

This milestone stops before those agentic behaviors.

## Files Involved

### `src/repopilot/validation/__init__.py`

Exports the validation package API.

What to learn:

- New workflow layers deserve their own package when they compose lower-level
  tools.
- A small export surface keeps future agent code easy to read.

### `src/repopilot/validation/models.py`

Defines `ValidationCheck` and `PatchValidationResult`.

What to learn:

- Validation output should be structured, not a loose console transcript.
- Future agents need machine-readable pass/fail data and command output.

### `src/repopilot/validation/pipeline.py`

Implements `apply_and_validate_patch()`.

What to learn:

- Composition layers should call existing safe tools rather than bypass them.
- Command allowlists should still be enforced at the composed workflow level.
- Pass/fail rules should be simple and deterministic.

### `tests/test_validation_pipeline.py`

Tests apply-before-validate ordering, pass/fail results, timeout behavior,
custom commands, default commands, error propagation, and deterministic output.

What to learn:

- Orchestration tests can monkeypatch lower-level tools to avoid slow or nested
  real command execution.
- Safety behavior includes proving commands do not run after apply failure.

## Interview Explanation

You can explain this feature like this:

"I added a validation pipeline that composes RepoPilot's safe patch applier and
safe command runner. It applies an approved patch first, then runs allowlisted
validation commands like pytest and Ruff. Each command result is structured with
stdout, stderr, return code, and timeout status, and the pipeline reports an
overall pass flag. It does not self-correct yet; it only creates the safe
apply-and-observe foundation for future failure analysis."
