from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from repopilot.tools import CommandToolError, run_command


def test_runs_allowed_successful_command(tmp_path: Path) -> None:
    command = _python_command("print('ok')")

    result = run_command(tmp_path, command, allowed_commands=[command])

    assert result.command == command
    assert result.return_code == 0
    assert result.stdout.strip() == "ok"
    assert result.stderr == ""
    assert result.timed_out is False


def test_captures_stdout(tmp_path: Path) -> None:
    command = _python_command("print('hello stdout')")

    result = run_command(tmp_path, command, allowed_commands=[command])

    assert "hello stdout" in result.stdout


def test_captures_stderr(tmp_path: Path) -> None:
    command = _python_command("import sys; print('hello stderr', file=sys.stderr)")

    result = run_command(tmp_path, command, allowed_commands=[command])

    assert "hello stderr" in result.stderr


def test_returns_nonzero_return_code_for_failing_allowed_command(
    tmp_path: Path,
) -> None:
    command = _python_command("import sys; print('failed'); sys.exit(7)")

    result = run_command(tmp_path, command, allowed_commands=[command])

    assert result.return_code == 7
    assert result.timed_out is False
    assert "failed" in result.stdout


def test_rejects_empty_command(tmp_path: Path) -> None:
    with pytest.raises(CommandToolError, match="must not be empty"):
        run_command(tmp_path, [], allowed_commands=[])


def test_rejects_disallowed_command(tmp_path: Path) -> None:
    command = _python_command("print('not allowed')")

    with pytest.raises(CommandToolError, match="not allowlisted"):
        run_command(tmp_path, command, allowed_commands=[["pytest"]])


def test_rejects_string_command(tmp_path: Path) -> None:
    with pytest.raises(CommandToolError, match="list of strings"):
        run_command(tmp_path, "pytest", allowed_commands=[["pytest"]])  # type: ignore[arg-type]


def test_handles_timeout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    command = _python_command("print('slow')")

    def fake_run(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired(
            cmd=kwargs.get("args", command),
            timeout=1,
            output="partial stdout",
            stderr="partial stderr",
        )

    monkeypatch.setattr("repopilot.tools.commands.subprocess.run", fake_run)

    result = run_command(tmp_path, command, allowed_commands=[command])

    assert result.return_code == -1
    assert result.stdout == "partial stdout"
    assert result.stderr == "partial stderr"
    assert result.timed_out is True


def test_uses_repo_root_as_cwd(tmp_path: Path) -> None:
    command = _python_command("import os; print(os.getcwd())")

    result = run_command(tmp_path, command, allowed_commands=[command])

    assert Path(result.stdout.strip()).resolve() == tmp_path.resolve()


def test_does_not_use_shell_true(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    command = _python_command("print('ok')")

    def fake_run(
        command_args: list[str],
        **kwargs: Any,
    ) -> subprocess.CompletedProcess[str]:
        assert command_args == command
        assert kwargs["shell"] is False
        return subprocess.CompletedProcess(
            args=command_args,
            returncode=0,
            stdout="ok\n",
            stderr="",
        )

    monkeypatch.setattr("repopilot.tools.commands.subprocess.run", fake_run)

    result = run_command(tmp_path, command, allowed_commands=[command])

    assert result.return_code == 0
    assert result.stdout == "ok\n"


def test_returns_deterministic_structured_result(tmp_path: Path) -> None:
    command = _python_command("print('stable')")

    first_result = run_command(tmp_path, command, allowed_commands=[command])
    second_result = run_command(tmp_path, command, allowed_commands=[command])

    assert first_result.model_dump() == second_result.model_dump()


def _python_command(code: str) -> list[str]:
    return [sys.executable, "-c", code]
