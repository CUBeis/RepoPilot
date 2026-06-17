# Learning Note 15: Self-Correction Orchestrator

## What Was Built

Milestone 16 adds a bounded orchestration layer for self-correction. The new
orchestrator accepts an initial `PatchProposal`, applies and validates it through
the existing validation pipeline, analyzes any failures, and optionally retries
with repair proposals that were supplied by the caller.

This is not a repair generator. It does not decide how to fix code. It only
controls the safe loop around proposals that already exist.

## Why Self-Correction Orchestration Matters

Agentic coding systems need a repeatable way to respond when validation fails.
The basic workflow is:

1. Apply an approved proposal.
2. Run validation commands.
3. Analyze failures.
4. Try a repair proposal if one is available.
5. Stop when the patch passes or the loop reaches a safe stopping point.

This milestone creates that control flow without adding hidden autonomy.

## Why The Orchestrator Composes Existing Safe Layers

The orchestrator reuses:

- `apply_and_validate_patch()` to apply approved patches and run allowlisted
  checks.
- `analyze_validation_result()` to convert failed command results into
  structured failure summaries.

Keeping these responsibilities separate makes the system easier to test and
safer to extend. The orchestrator does not write files directly, run subprocesses
directly, or inspect command output itself.

## Why Repair Proposals Are Injected

Repair proposals are passed into the loop instead of generated inside it. That
keeps Milestone 16 deterministic and avoids pretending that RepoPilot can repair
code on its own before a real repair-generation layer exists.

Later, an LLM-backed repair proposer can create those repair proposals. This
orchestrator will still be useful because it already knows how to validate each
attempt and when to stop.

## Why max_attempts Matters

`max_attempts` prevents runaway loops. Even when repair proposals are available,
the orchestrator stops after a bounded number of attempts. This matters for
safety, cost control, and predictable behavior.

The default is intentionally small:

```python
max_attempts = 2
```

That allows one initial attempt and one repair attempt unless the caller chooses
a different limit.

## Why This Still Does Not Call Real LLMs

This milestone does not call OpenAI, Anthropic, local models, or any other LLM
provider. It also does not generate new patches internally.

That boundary is important. The project now has orchestration, but it does not
yet have autonomous repair generation. This keeps the system explainable and
testable before adding probabilistic model behavior.

## Files Added

### `src/repopilot/agent/__init__.py`

Exports the public agent orchestration objects:

- `SelfCorrectionAttempt`
- `SelfCorrectionResult`
- `run_self_correction_loop`

This lets future code import the orchestration API from `repopilot.agent`.

### `src/repopilot/agent/models.py`

Defines the Pydantic models for the orchestration result.

`SelfCorrectionAttempt` stores one attempt:

- attempt number
- proposal used
- validation result
- failure analysis

`SelfCorrectionResult` stores the full loop result:

- all attempts
- whether the final state passed
- a clear stopped reason

### `src/repopilot/agent/orchestrator.py`

Implements `run_self_correction_loop()`.

The function:

- tries the initial proposal first
- validates each proposal with `apply_and_validate_patch()`
- analyzes each result with `analyze_validation_result()`
- stops when validation passes
- stops when `max_attempts` is reached
- stops when no repair proposal is available
- propagates patch application errors instead of hiding them

### `tests/test_self_correction_orchestrator.py`

Verifies that the loop:

- runs the initial proposal first
- stops on success
- analyzes failed validation results
- retries with supplied repair proposals
- respects `max_attempts`
- stops clearly when no repair proposal exists
- propagates patch application errors
- passes validation commands through unchanged
- returns deterministic structured output

## Stopped Reasons

The orchestrator returns a clear `stopped_reason`:

- `validation_passed`
- `max_attempts_reached`
- `no_repair_proposal_available`

These strings make the result easy for future agents, APIs, or CLI views to
explain.

## How This Prepares For Future LLM Repair Generation

Later milestones can add a repair generator that uses:

- the original issue
- the failed proposal
- `FailureAnalysis`
- relevant file reads

That layer can produce another `PatchProposal`. The orchestrator can then retry
with that proposal without changing its safety contract.

## How To Explain This In An Interview

You can describe this feature like this:

"I built a deterministic self-correction orchestrator that composes safe patch
application, validation command execution, and failure analysis. It does not
generate fixes itself. Instead, it accepts repair proposals from another layer,
validates each attempt, records structured failure context, and stops on success,
when max attempts are reached, or when no repair proposal is available. This
keeps the control loop safe and testable before adding LLM-generated repairs."
