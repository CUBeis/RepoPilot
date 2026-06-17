# 12 - Safe Command Runner

Milestone 13 adds a safe command runner. This is the first tool that can execute
validation commands such as `pytest` and `ruff`, but it does so through a narrow,
allowlisted interface.

This milestone does not call LLMs, edit files, apply patches, create API
endpoints, or self-correct from command failures.

## What Was Built

The main function is:

```python
run_command(
    root_path,
    command,
    timeout_seconds=30,
    allowed_commands=None,
)
```

It returns a `CommandResult` with:

- Command arguments
- Return code
- Captured stdout
- Captured stderr
- Whether the command timed out

The default allowlist includes:

```python
["pytest"]
["ruff", "check", "."]
["ruff", "format", "--check", "."]
```

## Why Agents Need Command Tools

Future RepoPilot agents need feedback from validation commands. After applying a
patch, an agent should be able to run tests or lint checks and inspect the
result.

Direct shell access is too broad. A command tool gives the agent a constrained
capability with typed inputs, typed outputs, clear errors, and a visible safety
policy.

## Why Allowlists Matter

The runner accepts commands as `list[str]` and only runs commands that exactly
match the allowlist.

This prevents a future agent from running arbitrary commands such as deleting
files, accessing unrelated directories, opening shells, or invoking unknown
programs.

The default allowlist is intentionally small because this milestone is about
validation, not general automation.

## Why `shell=True` Is Dangerous

Shell execution allows command strings to be interpreted by a shell. That can
enable pipes, redirects, command chaining, variable expansion, and injection
risks.

RepoPilot uses:

```python
subprocess.run(command, shell=False)
```

and requires `command` to be a list of arguments. That keeps execution direct
and avoids shell parsing.

## Timeout And Output Capture

The command runner captures stdout and stderr as text so future agents can read
test failures or lint output.

It also enforces a timeout. If a command times out, RepoPilot returns a
structured result with `timed_out=True` instead of hanging forever.

## Why This Still Does Not Self-Correct

Running a command is only observation.

This milestone does not:

- Decide how to fix failures
- Call an LLM with command output
- Apply another patch
- Retry tests
- Loop until success

Those behaviors belong to a future self-correction layer.

## How This Prepares RepoPilot For Validation

The workflow can now grow toward:

```text
apply approved patch -> run allowed validation command -> inspect result later
```

The command runner provides the safe execution primitive that future test
validation and self-correction milestones can build on.

## Files Involved

### `src/repopilot/tools/models.py`

Adds `CommandResult`.

What to learn:

- Command execution should return structured data.
- Captured stdout and stderr are future agent observations.

### `src/repopilot/tools/commands.py`

Implements `run_command()` and `CommandToolError`.

What to learn:

- Command tools should validate the root path.
- Commands should be passed as argument lists, not shell strings.
- Exact allowlists reduce the blast radius of future agent actions.
- Timeouts keep automation from hanging indefinitely.

### `tests/test_command_runner.py`

Tests successful commands, stdout, stderr, nonzero return codes, invalid inputs,
timeouts, working directory behavior, `shell=False`, and deterministic results.

What to learn:

- Tool tests should verify both behavior and safety properties.
- Monkeypatching can prove that subprocess is called with safe settings.

## Interview Explanation

You can explain this feature like this:

"I added a safe command runner so RepoPilot can eventually validate code changes
with commands like pytest and Ruff. It validates the repository root, accepts
commands only as argument lists, rejects anything outside an exact allowlist,
runs subprocess without shell=True, captures stdout and stderr, enforces
timeouts, and returns a typed result. It does not self-correct yet; it only
provides the safe command execution primitive future agent loops will use."
