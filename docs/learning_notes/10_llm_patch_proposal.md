# 10 - LLM Patch Proposal Generator

Milestone 11 adds an LLM-backed patch proposal generator. It accepts an
`ImplementationPlan`, read-only `FileReadResult` objects, and an injected
`LLMClient`, then asks the client for JSON that can be validated as a
`PatchProposal`.

This milestone still does not call a real OpenAI or Anthropic API. It does not
write files, apply patches, run shell commands, execute tests, create
embeddings, use a vector database, or add an API endpoint.

## What Was Built

The new function is:

```python
create_llm_patch_proposal(
    plan,
    file_reads,
    llm_client,
    model="fake-patch-proposer",
    temperature=0.0,
    max_tokens=None,
)
```

It performs this flow:

1. Validate the plan and read inputs.
2. Build a prompt from the implementation plan and file contents.
3. Send an `LLMRequest` through the injected `LLMClient`.
4. Parse the response content as JSON.
5. Validate the JSON as a `PatchProposal`.
6. Force `requires_approval=True`.
7. Validate that proposed target files were planned and read.

## Why FakeLLMClient Is Used

`FakeLLMClient` keeps this milestone deterministic. Tests can verify request
construction, prompt contents, JSON parsing, and validation without:

- API keys
- Network calls
- Provider SDKs
- Model nondeterminism
- Token costs

This is the same pattern used by the LLM-backed planner: prove the integration
shape first, then add real provider adapters later.

## Why Approval Is Required

The function forces `requires_approval=True` even if the LLM returns `false`.

This matters because LLM output should not decide whether code edits are safe to
apply. Approval is a RepoPilot safety rule, not a model preference. A future
human review or policy layer can inspect the proposal before any write tool is
allowed to run.

## Why JSON And Pydantic Validation Matter

LLM output starts as text. RepoPilot needs structured data before any future
agent can reason about proposed changes safely.

JSON parsing checks that the response is machine-readable. Pydantic validation
checks that the response matches the `PatchProposal` schema:

- Summary
- Target files
- Proposed changes
- Risks
- Approval flag

The function raises `LLMPatchProposalError` when JSON is invalid or the
structure does not match the schema.

## Safety Validation

After schema validation, RepoPilot applies project-specific safety checks:

- Proposed files must be listed in `plan.relevant_files`.
- Proposed files must appear in the read-only `FileReadResult` list.
- Changes must be listed in `target_files`.
- File reads outside the implementation plan are rejected before prompting.
- Duplicate file reads are rejected.

These checks prevent an LLM response from proposing edits to files that were not
planned or inspected.

## Why This Still Does Not Write Files

This layer only returns a `PatchProposal`. It does not call `write_text`, apply
diffs, mutate files, run commands, or execute tests.

That separation keeps the system reviewable:

```text
plan -> read files -> propose patch -> approval -> apply later
```

Milestone 11 stops at the proposal step.

## How This Connects Later

Future milestones can add:

1. A diff preview layer.
2. A human approval checkpoint.
3. A safe patch application tool.
4. Test and lint execution tools.
5. Self-correction from failed checks.
6. PR-ready summaries.

Because the LLM proposal generator already returns a typed `PatchProposal`, a
future executor can consume the same model without depending on raw LLM text.

## Files Involved

### `src/repopilot/patching/llm_proposal.py`

Defines `create_llm_patch_proposal()` and `LLMPatchProposalError`.

What to learn:

- LLM-backed features should depend on `LLMClient`, not a provider SDK.
- Prompt construction, JSON parsing, schema validation, and safety validation
  should be explicit steps.
- LLM output can be constrained by deterministic checks after generation.

### `tests/test_llm_patch_proposal.py`

Tests the LLM patch proposal generator with `FakeLLMClient`.

What to learn:

- LLM integration tests can be deterministic.
- Tests should inspect the request sent to the fake client.
- Negative tests are essential for invalid JSON, invalid schema, unsafe file
  targets, and no-write behavior.

### `docs/learning_notes/10_llm_patch_proposal.md`

Documents the milestone and how it fits into RepoPilot's safety-first agentic
workflow.

What to learn:

- Strong portfolio projects explain both the code and the safety boundary.
- This milestone is about validated structured output, not file mutation.

## Interview Explanation

You can explain this feature like this:

"I added an LLM-backed patch proposal generator that uses the same
provider-independent LLM client abstraction as the planner. It builds a prompt
from an implementation plan and safe read-only file results, sends it through an
injected client, expects JSON, validates the response as a PatchProposal, forces
approval to true, and rejects proposals for files that were not planned or read.
Tests use FakeLLMClient, so the behavior is deterministic and no real API calls
or file writes happen."
