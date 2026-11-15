from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from jotta.cli import main


def send(monkeypatch: pytest.MonkeyPatch, payload: object, *argv: str) -> int:
    text = payload if isinstance(payload, str) else json.dumps(payload)
    monkeypatch.setattr("sys.stdin", io.StringIO(text))
    return main([*argv, "hook", "pre-tool-use"])


def event(project: Path, command: str) -> dict[str, object]:
    return {
        "session_id": "s1",
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": command},
        "cwd": str(project),
    }


def hook_log(project: Path) -> list[dict[str, object]]:
    path = project / ".jotta" / "runtime" / "logs" / "hooks.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_allowed_call_exits_zero_silently(
    project: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    assert send(monkeypatch, event(project, "git status")) == 0
    captured = capsys.readouterr()
    assert (captured.out, captured.err) == ("", "")
    assert not (project / ".jotta" / "runtime" / "logs").exists()


def test_blocked_call_exits_two_explains_and_logs(
    project: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    assert send(monkeypatch, event(project, "git push --force origin main")) == 2
    message = capsys.readouterr().err
    assert message.startswith("Blocked by the Jotta policy (force-push):")
    [record] = hook_log(project)
    assert record["decision"] == "block"
    assert record["rule"] == "force-push"
    assert record["tool"] == "Bash"
    assert record["session_id"] == "s1"
    assert "git push --force" in str(record["input"])


def test_project_is_found_from_a_nested_working_directory(
    project: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    nested = project / "src"
    nested.mkdir()
    payload = {"tool_name": "Read", "tool_input": {"file_path": str(project / ".env")}, "cwd": str(nested)}
    assert send(monkeypatch, payload) == 2
    capsys.readouterr()
    assert hook_log(project)[0]["rule"] == "read-secrets"


def test_explicit_root_wins_over_the_event(
    project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    payload = event(project, "rm -rf ../shared")
    assert send(monkeypatch, payload, "--root", str(project)) == 2
    capsys.readouterr()
    assert hook_log(project)[0]["rule"] == "delete-outside-project"


def test_guard_works_outside_a_jotta_project(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    assert send(monkeypatch, event(tmp_path, "git reset --hard")) == 2
    assert "hard-reset" in capsys.readouterr().err
    assert send(monkeypatch, event(tmp_path, "rm -rf build")) == 0


@pytest.mark.parametrize("payload", ["not json", "[1, 2]"])
def test_invalid_event_is_a_non_blocking_error(
    payload: str, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    assert send(monkeypatch, payload) == 1
    assert capsys.readouterr().err.startswith("jotta hook:")


def test_empty_input_is_allowed(monkeypatch: pytest.MonkeyPatch) -> None:
    assert send(monkeypatch, "") == 0
