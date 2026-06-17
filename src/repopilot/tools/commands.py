from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from repopilot.tools.models import CommandResult

DEFAULT_ALLOWED_COMMANDS = [
    ["pytest"],
    ["ruff", "check", "."],
    ["ruff", "format", "--check", "."],
]


class CommandToolError(ValueError):
    """Raised when a command tool request is unsafe or invalid."""


def run_command(
    root_path: str | Path,
    command: list[str],
    *,
    timeout_seconds: int = 30,
    allowed_commands: list[list[str]] | None = None,
) -> CommandResult:
    """Run an allowlisted command inside a repository root."""

    root = _resolve_root(root_path)
    validated_command = _validate_command(command)
    allowlist = _validate_allowed_commands(allowed_commands)
    _ensure_allowed(command=validated_command, allowed_commands=allowlist)
    _validate_timeout(timeout_seconds)

    try:
        completed_process = subprocess.run(
            validated_command,
            cwd=root,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            shell=False,
            check=False,
        )
    except subprocess.TimeoutExpired as error:
        return CommandResult(
            command=validated_command,
            return_code=-1,
            stdout=_coerce_output(error.stdout),
            stderr=_coerce_output(error.stderr),
            timed_out=True,
        )
    except OSError as error:
        raise CommandToolError(
            f"Could not run command: {' '.join(validated_command)}"
        ) from error

    return CommandResult(
        command=validated_command,
        return_code=completed_process.returncode,
        stdout=completed_process.stdout,
        stderr=completed_process.stderr,
        timed_out=False,
    )


def _resolve_root(root_path: str | Path) -> Path:
    root = Path(root_path).expanduser()
    if not root.exists():
        raise CommandToolError(f"Repository root does not exist: {root}")
    if not root.is_dir():
        raise CommandToolError(f"Repository root is not a directory: {root}")
    return root.resolve()


def _validate_command(command: Any) -> list[str]:
    if not isinstance(command, list):
        raise CommandToolError("command must be a list of strings")
    if not command:
        raise CommandToolError("command must not be empty")
    if not all(isinstance(part, str) for part in command):
        raise CommandToolError("command must contain only strings")
    if any(part == "" for part in command):
        raise CommandToolError("command parts must not be empty")

    return list(command)


def _validate_allowed_commands(
    allowed_commands: list[list[str]] | None,
) -> list[list[str]]:
    raw_allowed_commands = (
        DEFAULT_ALLOWED_COMMANDS if allowed_commands is None else allowed_commands
    )

    if not isinstance(raw_allowed_commands, list):
        raise CommandToolError("allowed_commands must be a list of command lists")

    validated_allowed_commands: list[list[str]] = []
    for allowed_command in raw_allowed_commands:
        validated_allowed_commands.append(_validate_command(allowed_command))

    return validated_allowed_commands


def _ensure_allowed(
    *,
    command: list[str],
    allowed_commands: list[list[str]],
) -> None:
    if command not in allowed_commands:
        raise CommandToolError(f"Command is not allowlisted: {' '.join(command)}")


def _validate_timeout(timeout_seconds: int) -> None:
    if timeout_seconds <= 0:
        raise CommandToolError("timeout_seconds must be greater than 0")


def _coerce_output(output: str | bytes | None) -> str:
    if output is None:
        return ""
    if isinstance(output, bytes):
        return output.decode("utf-8", errors="replace")
    return output
