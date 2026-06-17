# 09 - Patch Proposal Layer

Milestone 10 adds a patch proposal layer. It accepts a structured
`ImplementationPlan` and read-only `FileReadResult` objects, then returns a
typed `PatchProposal`.

This milestone does not write files, generate real diffs, apply patches, run
tests, call an LLM, or use an agent framework. Its job is to define the safety
contract that future editing code must pass through.

## What A Patch Proposal Is

A patch proposal is a structured description of changes RepoPilot may want to
make later.

The proposal includes:

- A summary
- Target files
- Proposed file changes
- A reason for each proposed change
- Start and end lines
- Original content
- Proposed content
- Risks
- A `requires_approval` flag

For now, `proposed_content` intentionally matches `original_content`. That makes
the proposal a safe placeholder while the project builds validation and approval
boundaries before real editing.

## Why Proposal Comes Before Applying Patches

Writing files is a higher-risk action than reading files or planning. A proposal
layer creates a reviewable checkpoint between "the system thinks these files
matter" and "the system changes code on disk."

This matters because future RepoPilot agents should be able to show:

- Which files they intend to change
- Why each file is included
- What content was read
- What content would be written
- Whether human approval is required

## Why Approval Is Required

`PatchProposal.requires_approval` defaults to `True`.

This keeps the project aligned with human-in-the-loop agent design. Even after a
future editing layer exists, RepoPilot should be able to pause before writing
files and ask for approval or policy validation.

## How ImplementationPlan Connects To FileReadResult

The `ImplementationPlan` says which files look relevant and which plan steps
target them.

The `FileReadResult` proves that RepoPilot inspected a file through the safe
read-only tool layer.

The patch proposal layer connects them by requiring:

- Every plan target file must have a matching file read.
- Every file read must belong to the plan target files.
- Duplicate reads for the same path are rejected.
- Output paths remain the relative paths from the existing models.

## What Validation Protects Against

Validation prevents unsafe or confusing proposal states.

For example, the layer rejects:

- Plans with no relevant files
- Missing reads for planned files
- File reads for files outside the plan
- Duplicate file reads

These checks matter because future edit execution should not operate on files
that were not planned and inspected.

## Why This Is Still Not Editing

This layer does not call `write_text`, apply diffs, update files, run shell
commands, or execute tests. It only creates structured data.

That separation keeps RepoPilot easy to test and safer to extend. Editing,
patch application, test running, and self-correction can be added in later
milestones with their own safety checks.

## How This Prepares For Safe Patch Application

Future milestones can extend this layer by:

1. Generating real proposed content.
2. Showing proposals to a human or approval policy.
3. Applying approved changes with a separate file-writing tool.
4. Running tests and lint checks.
5. Self-correcting if validation fails.
6. Producing PR-ready summaries.

Because proposals are already structured, future code can inspect target files,
risks, and exact line ranges before applying anything.

## Files Involved

### `src/repopilot/patching/__init__.py`

Exports the public patch proposal API.

What to learn:

- Package exports keep future agent code from depending on internal module
  paths.
- The public surface is intentionally small: models, error type, and proposal
  function.

### `src/repopilot/patching/models.py`

Defines `ProposedFileChange` and `PatchProposal`.

What to learn:

- Patch-related data should be typed before any executor acts on it.
- `requires_approval` is part of the model because approval is a safety
  property, not just UI text.

### `src/repopilot/patching/proposal.py`

Implements `create_patch_proposal()` and `PatchProposalError`.

What to learn:

- Composition layers can validate existing models without duplicating planner or
  file-tool logic.
- Clear validation errors make future agent failures easier to debug.
- The function is deterministic and writes nothing to disk.

### `tests/test_patch_proposal.py`

Tests successful proposal creation, approval defaults, original content
preservation, deterministic output, validation errors, and no-write behavior.

What to learn:

- Safety layers need negative tests as much as happy-path tests.
- Tests can prove that a proposal function does not modify files.

## Interview Explanation

You can explain this feature like this:

"After adding planning and safe read-only file tools, I added a patch proposal
layer. It accepts an implementation plan and the files that were safely read,
validates that every planned target file was inspected, rejects extra or missing
reads, and returns a typed proposal with target files, reasons, original content,
proposed content, risks, and an approval requirement. It deliberately does not
write files yet, which creates a safe review checkpoint before future patch
application."
