# Learning Note 16: LLM Repair Proposal Generator

## What Was Built

This milestone adds a repair proposal generator:

```text
failed attempt
+ failure analysis
+ file reads
+ LLMClient
↓
PatchProposal
```

The new function is `create_llm_repair_proposal()`. It accepts a failed
`SelfCorrectionAttempt`, read-only `FileReadResult` objects, and an injected
`LLMClient`. It builds a repair prompt, sends an `LLMRequest`, expects JSON back,
and validates that JSON into the existing `PatchProposal` model.

## Why This Fits After Self-Correction Orchestration

Milestone 16 created a loop that can try supplied repair proposals. This
milestone creates one way to produce those proposals, while keeping the loop
itself simple.

The orchestrator still does not generate repairs internally. That separation is
important because generation and orchestration have different safety concerns.

## Why The Input Is A Failed Attempt

A repair proposal should respond to a specific failed validation attempt, not to
a vague request. The failed attempt contains:

- the proposal that was applied
- the validation result
- the structured failure analysis

That gives the repair generator enough context to ask: "What should change next
to address this failure?"

## Why Failure Analysis Matters

Raw command output can be noisy. `FailureAnalysis` turns failed checks into
structured, agent-readable context:

- which checks failed
- whether a timeout happened
- return codes
- stdout and stderr excerpts
- whether self-correction is needed

The repair prompt includes this structured analysis so a future real LLM can
focus on the validation failure instead of guessing.

## Why File Reads Are Included

The generator does not read files directly. It receives `FileReadResult` objects
from the safe read-only file tools.

That keeps filesystem access explicit. The repair generator sees only the file
content that another safe layer chose to provide.

## Safety Rules

The repair generator:

- rejects attempts that already passed validation
- rejects failure analysis that says self-correction is not needed
- validates the LLM response as JSON
- validates the JSON with the `PatchProposal` Pydantic model
- forces `requires_approval=True`
- rejects proposed changes for files outside the failed attempt
- rejects proposed changes for files that were not read
- does not apply patches
- does not run commands
- does not call real provider APIs by itself

Extra read-only context is allowed, but proposed writes remain constrained to
failed-attempt files that were actually read.

## Why FakeLLMClient Is Still Used

Tests use `FakeLLMClient` so behavior is deterministic. A fake client lets the
project verify prompt construction, request settings, JSON parsing, approval
forcing, and safety validation without network access or API keys.

Real provider clients can be added later behind the same `LLMClient` protocol.

## Files Added

### `src/repopilot/agent/repair.py`

Implements `create_llm_repair_proposal()` and `LLMRepairProposalError`.

It builds the repair prompt, sends an `LLMRequest`, parses JSON, validates the
resulting `PatchProposal`, and enforces repair-specific file safety rules.

### `tests/test_llm_repair_proposal.py`

Tests that the repair generator:

- sends a request through `FakeLLMClient`
- includes a system message
- includes the failed attempt, failure analysis, and file contents
- parses valid JSON into `PatchProposal`
- forces approval
- rejects invalid JSON
- rejects invalid proposal structures
- rejects passed attempts
- rejects proposed changes outside the failed attempt
- rejects proposed changes for unread files
- passes model settings through
- stays deterministic
- writes nothing to disk

### `src/repopilot/agent/__init__.py`

Exports `create_llm_repair_proposal` and `LLMRepairProposalError` from the
agent package.

## Why This Still Is Not Fully Autonomous

This milestone can produce a repair proposal, but it does not automatically
apply it. The result is still a `PatchProposal` that requires explicit approval
before the safe patch applier can write anything.

The project now has the pieces for a controlled loop, but the approval boundary
is still intact.

## How This Prepares For Future Work

Later, the self-correction orchestrator can be extended to request a repair
proposal after a failed attempt. That future layer can call
`create_llm_repair_proposal()`, inspect the returned proposal, request approval,
and then pass it back into the existing validation loop.

## How To Explain This In An Interview

You can describe this feature like this:

"After building a safe self-correction loop, I added a repair proposal generator
that converts a failed validation attempt, structured failure analysis, and
read-only file context into a validated patch proposal through an injected LLM
client. It uses JSON plus Pydantic validation, forces approval, and restricts
proposed writes to failed-attempt files that were actually read. This gives the
system a path toward LLM-generated repairs without giving the model direct write
or command execution access."
