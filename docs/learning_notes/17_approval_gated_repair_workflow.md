# Learning Note 17: Approval-Gated Repair Workflow

## What Was Built

Milestone 18 adds an approval-gated repair workflow. The new function is:

```python
prepare_repair_for_approval(
    failed_attempt,
    file_reads,
    llm_client,
)
```

It calls `create_llm_repair_proposal()` and wraps the generated
`PatchProposal` in a `RepairApprovalRequest`.

The workflow stops there. It does not apply the repair.

## Why Repair Generation And Repair Application Are Separate

Generating a repair proposal is not the same as applying it.

Repair generation is a reasoning step:

- inspect the failed attempt
- inspect failure analysis
- inspect read-only file context
- propose a patch

Repair application is a write step:

- validate paths
- compare current content
- write files
- run validation commands later

Keeping those steps separate protects RepoPilot from silently moving from model
output to disk mutation.

## Why Generated Repairs Must Be Reviewed

Even when a proposal comes from a structured `LLMClient` flow, it is still model
output. It may be wrong, incomplete, stale, or risky.

The approval workflow makes the boundary explicit:

```text
LLM repair proposal -> approval request -> future approval decision -> apply later
```

This is the human-in-the-loop checkpoint for repair attempts.

## What RepairApprovalRequest Represents

`RepairApprovalRequest` is a Pydantic model with:

- `failed_attempt`
- `repair_proposal`
- `approval_required`
- `summary`

It packages the generated repair together with the failed attempt that caused
it. That makes review easier because a future UI, API, or CLI can show both the
failure and the proposed fix.

## How This Protects The Approval Boundary

The workflow always sets:

```python
approval_required = True
```

It also defensively ensures the nested `PatchProposal` still has
`requires_approval=True`.

The function does not call:

- `apply_patch_proposal()`
- `apply_and_validate_patch()`
- `run_command()`
- `run_self_correction_loop()`

That means generating a repair cannot accidentally become applying a repair.

## How This Can Later Connect To UI Or API Approval

A future API endpoint could return `RepairApprovalRequest` to a frontend. The
user could review:

- the failed attempt
- validation failure summary
- target files
- original content
- proposed content
- risks

Only after approval would another endpoint or workflow pass the proposal into
the safe patch applier or self-correction loop.

## Why This Still Does Not Self-Apply Or Self-Correct

This milestone does not run another validation attempt. It does not edit files,
run tests, or loop.

It only prepares the approval payload.

That keeps the project honest about what has been automated and what still
requires a human or policy decision.

## Files Added Or Updated

### `src/repopilot/agent/models.py`

Adds `RepairApprovalRequest`, the structured approval checkpoint for generated
repair proposals.

### `src/repopilot/agent/repair_workflow.py`

Implements `prepare_repair_for_approval()`.

The function delegates repair generation to `create_llm_repair_proposal()` and
returns a `RepairApprovalRequest` without applying anything.

### `src/repopilot/agent/__init__.py`

Exports `RepairApprovalRequest` and `prepare_repair_for_approval` from the agent
package.

### `tests/test_repair_workflow.py`

Tests that the workflow:

- calls the repair proposal generator
- returns a `RepairApprovalRequest`
- requires approval
- includes the failed attempt
- includes the generated repair proposal
- has a clear summary
- does not apply patches
- does not run validation commands
- does not call the self-correction loop
- propagates repair generation errors
- passes model settings through
- stays deterministic

## How To Explain This In An Interview

You can explain this feature like this:

"I added an approval-gated repair workflow that turns an LLM-generated repair
proposal into a reviewable approval request. It takes a failed self-correction
attempt, read-only file context, and an injected LLM client, then returns the
repair proposal together with the failed attempt and an explicit approval flag.
It does not apply the patch, run tests, or re-enter the self-correction loop.
That keeps the human approval checkpoint intact before any generated repair can
touch files."
