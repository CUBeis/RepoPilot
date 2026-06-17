# Learning Note 19: CLI Demo Command

## What Was Built

Milestone 20 adds a small command-line interface for RepoPilot.

The first command is:

```powershell
repopilot report-demo
```

It prints a sample `AgentRunReport` Markdown summary.

## Why A CLI Is Useful For Demos

A CLI makes RepoPilot easier to show without building a frontend or API endpoint
first. It gives the project a fast way to demonstrate output in a terminal.

For a portfolio project, this matters because reviewers can run one command and
see the shape of RepoPilot's reporting layer immediately.

## Why The First CLI Command Is Read-Only And In-Memory

The first CLI command deliberately avoids real repository work. It does not:

- scan a repository
- read files
- write files
- run validation commands
- call LLMs
- apply patches

Instead, it builds a tiny sample run from existing Pydantic models in memory.
That keeps the demo safe and deterministic.

## How It Uses The Reporting Layer

The command creates sample objects:

- `ImplementationPlan`
- `PatchProposal`
- `PatchValidationResult`

Then it calls:

```python
create_agent_run_report(...)
```

Finally, it prints:

```python
report.markdown_summary
```

This proves the reporting layer is useful as a presentation boundary.

## Why It Does Not Execute Agent Tools Yet

Future CLI commands may scan repositories, build context, propose patches, or
run validation commands. Those actions need approval rules, path validation,
command allowlists, and clear UX.

This milestone only demonstrates output. It keeps execution out of the CLI until
the workflow is ready to expose safely.

## How This Prepares For Future Commands

The CLI now has:

- an argparse entry point
- a `report-demo` subcommand
- a console script in `pyproject.toml`
- tests for output and no side effects

Future commands can follow the same shape:

```text
parse args -> call safe RepoPilot layer -> print structured result
```

## Files Added Or Updated

### `src/repopilot/cli.py`

Defines `main()` and the `report-demo` subcommand.

The command builds a sample report in memory and prints Markdown.

### `pyproject.toml`

Adds the console script:

```toml
[project.scripts]
repopilot = "repopilot.cli:main"
```

### `tests/test_cli.py`

Tests that the command:

- prints `# RepoPilot Run Report`
- includes the issue
- includes the status
- includes planned, proposed, and changed files
- returns exit code `0`
- does not call LLMs
- does not run commands
- does not apply patches
- does not scan repositories
- produces deterministic output

### `README.md`

Documents how to run:

```powershell
repopilot report-demo
```

## How To Explain This In An Interview

You can explain this feature like this:

"I added a small CLI entry point to demonstrate RepoPilot's reporting layer. The
first command, `repopilot report-demo`, builds an in-memory sample run report and
prints a Markdown summary. It does not scan repositories, call LLMs, run
commands, or write files. This gives the project a safe demo surface while
setting up the command structure for future real workflows."
