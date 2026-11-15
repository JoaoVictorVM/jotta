from __future__ import annotations

import io
import json
import sys
from pathlib import Path

import pytest

from jotta.cli import main
from jotta.core.paths import ProjectPaths
from jotta.hooks.smoke import after_edit, is_code

PYTHON = f'"{sys.executable}"'
LINT_FAILURE = f"{PYTHON} -c \"import sys; print('app.py:3:1: E999 SyntaxError: invalid syntax'); sys.exit(1)\""
PASSING = f'{PYTHON} -c "print(1)"'


def configure(project: Path, commands: list[str], debounce: float = 20) -> None:
    gates = project / ".jotta" / "sensors" / "computational" / "gates.json"
    data = json.loads(gates.read_text(encoding="utf-8"))
    data["profiles"]["smoke"] = commands
    data["post_edit"] = {"profile": "smoke", "debounce_seconds": debounce}
    gates.write_text(json.dumps(data), encoding="utf-8")


def edit_event(project: Path, file_path: str = "src/app.py", tool: str = "Edit") -> dict[str, object]:
    return {"tool_name": tool, "tool_input": {"file_path": file_path}, "cwd": str(project)}


def send(monkeypatch: pytest.MonkeyPatch, payload: dict[str, object]) -> int:
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
    return main(["hook", "post-tool-use"])


def test_a_lint_failure_reaches_the_agent_right_after_the_edit(
    project: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    configure(project, [LINT_FAILURE])
    assert send(monkeypatch, edit_event(project)) == 2
    message = capsys.readouterr().err
    assert message.startswith("The smoke quality profile failed after this edit.")
    assert "E999 SyntaxError" in message
    assert "Full log: .jotta/runtime/logs/" in message
    assert "Receipt: .jotta/runtime/receipts/" in message


def test_a_passing_profile_stays_silent(
    project: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    configure(project, [PASSING])
    assert send(monkeypatch, edit_event(project)) == 0
    captured = capsys.readouterr()
    assert (captured.out, captured.err) == ("", "")
    state = json.loads((project / ".jotta" / "runtime" / "state" / "post-edit.json").read_text(encoding="utf-8"))
    assert state["status"] == "passed"
    assert (project / state["receipt"]).is_file()


def test_a_burst_of_edits_runs_the_profile_once(project: Path) -> None:
    configure(project, [PASSING], debounce=20)
    paths = ProjectPaths(project)
    assert after_edit(edit_event(project), paths, clock=1000.0).status == "passed"
    assert after_edit(edit_event(project, "src/b.py"), paths, clock=1005.0).status == "debounced"
    assert json.loads((paths.state / "post-edit.json").read_text(encoding="utf-8"))["pending"] is True
    assert after_edit(edit_event(project, "src/c.py"), paths, clock=1021.0).status == "passed"
    assert len(list((paths.runtime / "receipts").iterdir())) == 2


def test_a_failure_is_rechecked_without_waiting(project: Path) -> None:
    configure(project, [LINT_FAILURE], debounce=20)
    paths = ProjectPaths(project)
    assert after_edit(edit_event(project), paths, clock=1000.0).status == "failed"
    configure(project, [PASSING], debounce=20)
    assert after_edit(edit_event(project), paths, clock=1001.0).status == "passed"
    assert after_edit(edit_event(project), paths, clock=1002.0).status == "debounced"


@pytest.mark.parametrize(
    ("payload_changes", "status"),
    [
        ({"tool_name": "Read"}, "ignored"),
        ({"tool_input": {"file_path": "README.md"}}, "ignored"),
        ({"tool_input": {"file_path": ".planning/features/F01/plan.md"}}, "ignored"),
        ({"tool_input": {"file_path": ".jotta/config.yaml"}}, "ignored"),
        ({"tool_input": "src/app.py"}, "ignored"),
    ],
)
def test_non_code_edits_are_ignored(project: Path, payload_changes: dict[str, object], status: str) -> None:
    configure(project, [LINT_FAILURE])
    payload = {**edit_event(project), **payload_changes}
    assert after_edit(payload, ProjectPaths(project)).status == status


def test_an_empty_profile_does_nothing(project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    assert after_edit(edit_event(project), ProjectPaths(project)).status == "not-configured"
    assert send(monkeypatch, edit_event(project)) == 0
    assert not (project / ".jotta" / "runtime" / "receipts").exists()


def test_outside_a_jotta_project_the_hook_does_nothing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    assert send(monkeypatch, edit_event(tmp_path)) == 0


@pytest.mark.parametrize(
    ("path", "code"),
    [("src/app.py", True), ("web/App.tsx", True), ("Makefile", True), ("docs/guide.md", False), (".git/config", False)],
)
def test_is_code(path: str, code: bool) -> None:
    assert is_code(path) is code
