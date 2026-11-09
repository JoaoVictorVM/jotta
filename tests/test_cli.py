from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from jotta import __version__
from jotta.cli import EXIT_NOT_IMPLEMENTED, EXIT_OK, EXIT_USAGE, main

SRC = Path(__file__).resolve().parents[1] / "src"
COMMANDS = [
    "install",
    "doctor",
    "status",
    "validate-prd",
    "sync-tasks",
    "progress",
    "prepare",
    "checkpoint",
    "finish",
    "gate",
    "budget",
    "models",
    "quality",
    "orca",
]


def test_help_lists_every_command(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exit_info:
        main(["--help"])
    assert exit_info.value.code == 0
    output = capsys.readouterr().out
    for command in COMMANDS:
        assert command in output


def test_version_flag_prints_package_version(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exit_info:
        main(["--version"])
    assert exit_info.value.code == 0
    assert capsys.readouterr().out.strip() == f"jotta {__version__}"


def test_without_command_prints_help(capsys: pytest.CaptureFixture[str]) -> None:
    assert main([]) == EXIT_OK
    assert "usage: jotta" in capsys.readouterr().out


def test_install_is_not_implemented_yet(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["install"]) == EXIT_NOT_IMPLEMENTED
    assert "not implemented yet" in capsys.readouterr().err


def test_unknown_command_is_a_usage_error() -> None:
    with pytest.raises(SystemExit) as exit_info:
        main(["unknown"])
    assert exit_info.value.code == EXIT_USAGE


@pytest.mark.parametrize("command", ["gate", "budget", "models", "orca"])
def test_grouped_commands_require_a_subcommand(command: str) -> None:
    with pytest.raises(SystemExit) as exit_info:
        main([command])
    assert exit_info.value.code == EXIT_USAGE


def test_project_command_outside_a_project_is_a_usage_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    assert main(["status"]) == EXIT_USAGE
    assert "no Jotta project found" in capsys.readouterr().err


def test_module_entry_point_runs() -> None:
    env = {**os.environ, "PYTHONPATH": str(SRC)}
    result = subprocess.run(
        [sys.executable, "-m", "jotta", "--version"],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert result.returncode == 0
    assert result.stdout.strip() == f"jotta {__version__}"
