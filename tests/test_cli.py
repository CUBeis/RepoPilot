from pathlib import Path
from typing import Any

import pytest

from repopilot.cli import main
from repopilot.llm import FakeLLMClient


def test_cli_report_demo_prints_heading(capsys: pytest.CaptureFixture[str]) -> None:
    main(["report-demo"])

    output = capsys.readouterr().out

    assert "# RepoPilot Run Report" in output


def test_cli_report_demo_output_includes_issue(
    capsys: pytest.CaptureFixture[str],
) -> None:
    main(["report-demo"])

    output = capsys.readouterr().out

    assert "**Issue:** Fix login flow validation" in output


def test_cli_report_demo_output_includes_status(
    capsys: pytest.CaptureFixture[str],
) -> None:
    main(["report-demo"])

    output = capsys.readouterr().out

    assert "**Status:** validated" in output


def test_cli_report_demo_output_includes_file_sections(
    capsys: pytest.CaptureFixture[str],
) -> None:
    main(["report-demo"])

    output = capsys.readouterr().out

    assert "- Planned: src/auth.py, tests/test_auth.py" in output
    assert "- Proposed: src/auth.py" in output
    assert "- Changed: src/auth.py" in output


def test_main_returns_zero_for_report_demo(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main(["report-demo"])
    capsys.readouterr()

    assert exit_code == 0


def test_cli_does_not_call_llms_run_commands_apply_patches_or_scan(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    marker = tmp_path / "marker.txt"
    marker.write_text("unchanged", encoding="utf-8")

    def fail_generate(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("LLM client should not be called")

    def fail_run_command(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("run_command should not be called")

    def fail_apply_patch(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("apply_patch_proposal should not be called")

    def fail_scan_repository(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("scan_repository should not be called")

    monkeypatch.setattr(FakeLLMClient, "generate", fail_generate)
    monkeypatch.setattr("repopilot.tools.commands.run_command", fail_run_command)
    monkeypatch.setattr(
        "repopilot.patching.applier.apply_patch_proposal",
        fail_apply_patch,
    )
    monkeypatch.setattr(
        "repopilot.repository.scanner.scan_repository",
        fail_scan_repository,
    )

    main(["report-demo"])
    capsys.readouterr()

    assert marker.read_text(encoding="utf-8") == "unchanged"


def test_cli_report_demo_output_is_deterministic(
    capsys: pytest.CaptureFixture[str],
) -> None:
    main(["report-demo"])
    first = capsys.readouterr().out

    main(["report-demo"])
    second = capsys.readouterr().out

    assert first == second
