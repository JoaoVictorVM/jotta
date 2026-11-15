from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from jotta.cli import main
from jotta.core.state import JSONDict

SPEC = """# Spec: Tela inicial

| File Path | New/Modified | Purpose | Key Responsibilities |
|---|---|---|---|
| `src/home.py` | New | Screen | Render |
| `tests/` | New | Tests | Cover the screen |
"""


PRD = """# PRD

| ID | Feature | Priority | Dependencies |
|---|---|---|---|
| F03 | Tela inicial | 1 | none |

**Wave 1**: F03
"""


@pytest.fixture
def feature(project: Path) -> Path:
    (project / ".planning" / "PRD.md").write_text(PRD, encoding="utf-8")
    folder = project / ".planning" / "features" / "F03-tela-inicial"
    folder.mkdir(parents=True)
    (folder / "spec.md").write_text(SPEC, encoding="utf-8")
    return project


def prepare(project: Path, capsys: pytest.CaptureFixture[str], *extra: str) -> JSONDict:
    assert main(["--root", str(project), "prepare", "F03", *extra]) == 0
    capsys.readouterr()
    run = json.loads((project / ".jotta" / "runtime" / "state" / "current-run.json").read_text(encoding="utf-8"))
    packet: JSONDict = json.loads((project / run["context_packet"]).read_text(encoding="utf-8"))
    return packet


def edit(monkeypatch: pytest.MonkeyPatch, project: Path, file_path: str, tool: str = "Edit") -> int:
    payload = {"tool_name": tool, "tool_input": {"file_path": file_path}, "cwd": str(project)}
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
    return main(["hook", "pre-tool-use"])


def shell(monkeypatch: pytest.MonkeyPatch, project: Path, command: str) -> int:
    payload = {"tool_name": "Bash", "tool_input": {"command": command}, "cwd": str(project)}
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
    return main(["hook", "pre-tool-use"])


def hook_log(project: Path) -> list[JSONDict]:
    path = project / ".jotta" / "runtime" / "logs" / "hooks.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_prepare_records_the_scope_from_the_spec_and_the_command_line(
    feature: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    packet = prepare(feature, capsys, "--profile", "strict", "--allow", "docs/home.md")
    assert packet["allowed_paths"] == ["src/home.py", "tests/", "docs/home.md"]
    assert packet["scope_enforcement"] == "block"
    assert packet["scope_additions"] == []


def test_strict_blocks_an_edit_outside_the_scope(
    feature: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    prepare(feature, capsys, "--profile", "strict")
    assert edit(monkeypatch, feature, "src/home.py") == 0
    assert edit(monkeypatch, feature, str(feature / "tests" / "test_home.py"), tool="Write") == 0
    assert edit(monkeypatch, feature, ".planning/features/F03-tela-inicial/progress.md") == 0
    capsys.readouterr()

    assert edit(monkeypatch, feature, "src/payments.py") == 2
    message = capsys.readouterr().err
    assert "edit-outside-task-scope" in message
    assert "'src/payments.py'" in message
    assert "jotta scope allow" in message
    assert hook_log(feature)[-1]["decision"] == "block"


def test_lean_warns_about_an_edit_outside_the_scope(
    feature: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    packet = prepare(feature, capsys, "--profile", "lean")
    assert packet["scope_enforcement"] == "warn"
    assert edit(monkeypatch, feature, "src/payments.py") == 0
    warning = json.loads(capsys.readouterr().out)
    assert warning["systemMessage"].startswith("Jotta warning (edit-outside-task-scope):")
    record = hook_log(feature)[-1]
    assert (record["decision"], record["rule"]) == ("warn", "edit-outside-task-scope")


def test_manual_classic_does_not_check_the_scope(
    feature: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    prepare(feature, capsys, "--profile", "manual-classic")
    assert edit(monkeypatch, feature, "src/payments.py") == 0
    assert capsys.readouterr().out == ""


def test_no_declared_paths_means_no_check(
    project: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    packet = prepare(project, capsys, "--profile", "strict")
    assert packet["allowed_paths"] == []
    assert edit(monkeypatch, project, "anything.py") == 0


def test_a_finished_run_no_longer_restricts_edits(
    feature: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    prepare(feature, capsys, "--profile", "strict")
    assert main(["--root", str(feature), "finish", "--status", "completed-local"]) == 0
    capsys.readouterr()
    assert edit(monkeypatch, feature, "src/payments.py") == 0


def test_a_person_can_widen_the_scope(
    feature: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    prepare(feature, capsys, "--profile", "strict")
    root = str(feature)
    assert main(["--root", root, "scope", "allow", "src/payments.py", "--reason", "shared helper"]) == 0
    shown = json.loads(capsys.readouterr().out)
    assert "src/payments.py" in shown["allowed_paths"]
    assert shown["additions"][0]["reason"] == "shared helper"
    assert edit(monkeypatch, feature, "src/payments.py") == 0


@pytest.mark.parametrize(
    "command",
    [
        "jotta scope allow src/payments.py --reason x",
        "jotta --root . scope allow src --reason x",
        "python -m jotta scope allow src --reason x",
    ],
)
def test_the_agent_cannot_widen_its_own_scope(
    feature: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], command: str
) -> None:
    assert shell(monkeypatch, feature, command) == 2
    assert "widen-scope" in capsys.readouterr().err


def test_the_agent_can_read_the_scope(
    feature: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    assert shell(monkeypatch, feature, "jotta scope show") == 0


def test_edits_inside_a_worker_worktree_are_checked(
    feature: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    prepare(feature, capsys, "--profile", "strict")
    state = feature / ".jotta" / "runtime" / "state" / "current-run.json"
    run = json.loads(state.read_text(encoding="utf-8"))
    worktree = tmp_path / "worktree"
    run["status"] = "running"
    run["workers"] = [{"role": "implementer", "worktree_path": str(worktree)}]
    state.write_text(json.dumps(run), encoding="utf-8")
    assert edit(monkeypatch, feature, str(worktree / "src" / "home.py")) == 0
    assert edit(monkeypatch, feature, str(worktree / "src" / "payments.py")) == 2
    capsys.readouterr()


def test_scope_without_a_prepared_task_is_invalid(project: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--root", str(project), "scope", "show"]) == 2
    assert json.loads(capsys.readouterr().out)["status"] == "invalid"
