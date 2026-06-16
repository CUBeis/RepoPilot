# 08 - Safe Read-Only File Tools

Milestone 9 adds safe read-only file tools. These tools let future agents inspect
repository files without writing files, generating patches, or running shell
commands.

## What Read-Only Tools Are

Read-only tools are controlled functions that expose a narrow filesystem
capability. In this milestone, RepoPilot can:

- Read a whole UTF-8 text file with size and line limits
- Read a specific inclusive line range
- Return structured metadata about the read

The tools return `FileReadResult` objects with:

- Relative path
- Start line
- End line
- Content
- Total lines
- File size in bytes

## Why Agents Need Tools Instead Of Direct Filesystem Access

Future agents should not freely access the filesystem. They should use explicit
tools with validation, clear errors, and traceable inputs and outputs.

That makes behavior easier to test, observe, and constrain.

## Why Path Safety Matters

The tools accept a repository root and a relative path. They reject:

- Absolute paths
- Path traversal such as `../secret.txt`
- Missing files
- Directories
- Invalid UTF-8 or binary-looking content

This prevents a future agent from accidentally reading files outside the target
repository.

## Why Read-Only Comes Before Editing

Reading is lower risk than editing. Before RepoPilot can safely change files, it
needs trusted inspection tools.

This milestone deliberately does not write files, create patches, run commands,
or execute tests.

## How These Tools Connect To The Planner

The planner produces target files and steps. Future agent layers can use these
read-only tools to inspect those target files before proposing edits.

For example:

1. Planner identifies `src/auth.py`.
2. Read-only tool reads the relevant line range.
3. Future patch generator proposes a change.
4. Human approval or policy checks can happen before writing.

## How These Tools Connect Later

Read-only file tools prepare RepoPilot for:

- Patch generation
- Human approval checkpoints
- Test execution tools
- Self-correction loops
- Pull request summaries

They form the safe inspection layer before higher-risk actions.

## Files Involved

### `src/repopilot/tools/__init__.py`

Exports the safe tool API.

What to learn:

- Tool modules should expose only the functions future agents are allowed to use.

### `src/repopilot/tools/models.py`

Defines `FileReadResult`.

What to learn:

- Tool outputs should be structured, typed, and easy to log.
- Returning metadata with content makes later agent decisions traceable.

### `src/repopilot/tools/filesystem.py`

Implements safe read-only filesystem operations.

What to learn:

- Path validation should happen before reading.
- Resolved paths must stay inside the repository root.
- Binary and invalid UTF-8 files should fail clearly.
- Safety limits protect future agents from reading huge files into context.

### `tests/test_file_tools.py`

Tests read-only file behavior with temporary directories.

What to learn:

- Filesystem tools need safety-focused tests.
- Tests cover successful reads, line ranges, path traversal, absolute paths,
  missing files, directories, invalid ranges, limits, invalid UTF-8, and
  determinism.

## Interview Explanation

You can explain this feature like this:

"I added safe read-only file tools so future RepoPilot agents can inspect
repository files through a constrained interface instead of directly touching the
filesystem. The tools reject absolute paths and traversal, enforce size and line
limits, read UTF-8 text only, and return structured metadata. This creates a safe
inspection layer before adding patch generation or file editing."
