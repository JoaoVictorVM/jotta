from __future__ import annotations

import io
import json
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path

import pytest

from jotta.cli import main
from jotta.core.paths import ProjectPaths
from jotta.hooks import policy

PYTHON = f'"{sys.executable}"'
PASSING = f'{PYTHON} -c "print(1)"'
FAILING = f"{PYTHON} -c \"import sys; print('app.py:1:1: E999 broken'); sys.exit(1)\""
PRD = """# PRD

| ID | Feature | Priority | Dependencies |
|---|---|---|---|
| F03 | Tela inicial | 1 | none |
"""


def git(project: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@example.com", *args],
        cwd=project,
        check=True,
        capture_output=True,
    )


def set_smoke(project: Path, commands: list[str]) -> None:
    gates = project / ".jotta" / "sensors" / "computational" / "gates.json"
    data = json.loads(gates.read_text(encoding="utf-8"))
    data["profiles"]["smoke"] = commands
    gates.write_text(json.dumps(data, indent=2), encoding="utf-8")


@pytest.fixture
def repo(project: Path) -> Path:
    """A project whose harness, PRD and quality gates are committed."""
    (project / ".planning" / "PRD.md").write_text(PRD, encoding="utf-8")
    git(project, "init", "-q")
    git(project, "add", "-A")
    git(project, "commit", "-q", "-m", "init")
    return project


def commit_gates(project: Path) -> None:
    git(project, "add", ".jotta/sensors/computational/gates.json")
    git(project, "commit", "-q", "-m", "gates")


def hook(monkeypatch: pytest.MonkeyPatch, event: str, payload: Mapping[str, object]) -> int:
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
    return main(["hook", event])


def edit(project: Path, path: str = "src/app.py", session: str = "s1") -> dict[str, object]:
    return {
        "session_id": session,
        "hook_event_name": "PostToolUse",
        "tool_name": "Edit",
        "tool_input": {"file_path": str(project / path)},
        "cwd": str(project),
    }


def stop_event(project: Path) -> dict[str, object]:
    return {"session_id": "s1", "hook_event_name": "Stop", "stop_hook_active": False, "cwd": str(project)}


def test_an_uncommitted_edit_does_not_switch_off_the_post_edit_check(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    set_smoke(repo, [FAILING])
    commit_gates(repo)
    set_smoke(repo, [])
    assert hook(monkeypatch, "post-tool-use", edit(repo)) == 2
    assert "E999 broken" in capsys.readouterr().err
    commit_gates(repo)
    assert hook(monkeypatch, "post-tool-use", edit(repo, "src/b.py")) == 0


def test_a_receipt_from_edited_gates_does_not_release_the_stop(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    set_smoke(repo, [PASSING])
    commit_gates(repo)
    assert main(["--root", str(repo), "prepare", "F03", "--profile", "lean"]) == 0
    set_smoke(repo, [])
    main(["--root", str(repo), "quality", "smoke"])
    capsys.readouterr()
    assert hook(monkeypatch, "stop", stop_event(repo)) == 2
    assert "differ from the committed quality gates" in capsys.readouterr().err
    set_smoke(repo, [PASSING])
    main(["--root", str(repo), "quality", "smoke"])
    capsys.readouterr()
    assert hook(monkeypatch, "stop", stop_event(repo)) == 0


def test_an_untracked_harness_is_pinned_for_the_session(
    project: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    set_smoke(project, [FAILING])
    assert hook(monkeypatch, "post-tool-use", edit(project)) == 2
    set_smoke(project, [])
    assert hook(monkeypatch, "post-tool-use", edit(project, "src/b.py")) == 2
    capsys.readouterr()
    assert hook(monkeypatch, "post-tool-use", edit(project, "src/c.py", session="s2")) == 0


def test_a_divergence_is_reported_once_per_session(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    payload = {
        "session_id": "s1",
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": "git status"},
        "cwd": str(repo),
    }
    assert hook(monkeypatch, "pre-tool-use", payload) == 0
    assert capsys.readouterr().out == ""
    set_smoke(repo, ["make lint"])
    assert hook(monkeypatch, "pre-tool-use", payload) == 0
    message = json.loads(capsys.readouterr().out)["systemMessage"]
    assert message.startswith("Jotta warning (policy-not-committed): .jotta/sensors/computational/gates.json")
    assert "until they are committed" in message
    assert hook(monkeypatch, "pre-tool-use", payload) == 0
    assert capsys.readouterr().out == ""


def test_the_policy_snapshot_cannot_be_edited(
    project: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    payload = {
        "session_id": "s1",
        "hook_event_name": "PreToolUse",
        "tool_name": "Write",
        "tool_input": {"file_path": ".jotta/runtime/state/policy-snapshot.json", "content": "{}"},
        "cwd": str(project),
    }
    assert hook(monkeypatch, "pre-tool-use", payload) == 2
    assert "(edit-policy-snapshot)" in capsys.readouterr().err


def test_doctor_warns_when_committed_gates_differ(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    main(["--root", str(repo), "doctor"])
    assert "differs from the version the hooks enforce" not in capsys.readouterr().out
    set_smoke(repo, ["make lint"])
    main(["--root", str(repo), "doctor"])
    assert "gates.json differs from the version the hooks enforce (HEAD)" in capsys.readouterr().out


def test_without_git_or_session_the_working_tree_is_used(project: Path) -> None:
    paths = ProjectPaths(project)
    pinned = policy.pin(paths, paths.gates, None)
    assert (pinned.source, pinned.diverges) == ("working tree", False)
    assert policy.load_gates(paths, None)["profiles"]["smoke"] == []
    assert policy.committed(paths, paths.gates) is None


def test_unreadable_pinned_gates_count_as_empty(project: Path) -> None:
    paths = ProjectPaths(project)
    paths.gates.write_text("{oops", encoding="utf-8")
    assert policy.load_gates(paths, None) == {}
    assert policy.same(None, None) and not policy.same("a", None) and policy.same("a\r\n", "a\n")
