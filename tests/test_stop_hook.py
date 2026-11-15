from __future__ import annotations

import io
import json
import sys
import time
from pathlib import Path

import pytest

from jotta.cli import main
from jotta.core.paths import ProjectPaths
from jotta.core.state import JSONDict
from jotta.hooks.smoke import after_edit

PYTHON = f'"{sys.executable}"'
PASSING = f'{PYTHON} -c "print(1)"'
FAILING = f'{PYTHON} -c "import sys; sys.exit(1)"'
PRD = """# PRD

| ID | Feature | Priority | Dependencies |
|---|---|---|---|
| F03 | Tela inicial | 1 | none |
"""


@pytest.fixture
def task(project: Path) -> Path:
    (project / ".planning" / "PRD.md").write_text(PRD, encoding="utf-8")
    return project


def configure(project: Path, **profiles: list[str]) -> None:
    gates = project / ".jotta" / "sensors" / "computational" / "gates.json"
    data = json.loads(gates.read_text(encoding="utf-8"))
    data["profiles"].update(profiles)
    gates.write_text(json.dumps(data), encoding="utf-8")


def prepare(project: Path, profile: str, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--root", str(project), "prepare", "F03", "--profile", profile]) == 0
    capsys.readouterr()


def quality(project: Path, profile: str, capsys: pytest.CaptureFixture[str]) -> None:
    main(["--root", str(project), "quality", profile])
    capsys.readouterr()


def stop(monkeypatch: pytest.MonkeyPatch, project: Path) -> int:
    payload = {"hook_event_name": "Stop", "stop_hook_active": False, "cwd": str(project)}
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
    return main(["hook", "stop"])


def current_run(project: Path) -> JSONDict:
    data: JSONDict = json.loads(
        (project / ".jotta" / "runtime" / "state" / "current-run.json").read_text(encoding="utf-8")
    )
    return data


def test_without_a_prepared_task_the_agent_may_stop(project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    assert stop(monkeypatch, project) == 0


def test_an_active_task_without_a_receipt_cannot_stop(
    task: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    configure(task, smoke=[PASSING])
    prepare(task, "lean", capsys)
    assert stop(monkeypatch, task) == 2
    message = capsys.readouterr().err
    assert message.startswith("Task F03 is still active and has no `smoke` quality receipt")
    assert "jotta quality smoke" in message
    assert "jotta checkpoint --status blocked" in message


def test_a_passing_receipt_lets_the_agent_stop(
    task: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    configure(task, smoke=[PASSING])
    prepare(task, "lean", capsys)
    quality(task, "smoke", capsys)
    assert stop(monkeypatch, task) == 0


def test_a_failed_receipt_keeps_the_agent_working(
    task: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    configure(task, smoke=[FAILING])
    prepare(task, "lean", capsys)
    quality(task, "smoke", capsys)
    assert stop(monkeypatch, task) == 2
    assert "with status `failed`" in capsys.readouterr().err


def test_an_edit_after_the_receipt_requires_a_new_one(
    task: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    configure(task, smoke=[PASSING])
    prepare(task, "lean", capsys)
    quality(task, "smoke", capsys)
    configure(task, smoke=[])
    edit = {"tool_name": "Edit", "tool_input": {"file_path": "src/home.py"}}
    after_edit(edit, ProjectPaths(task), clock=time.time() + 5)
    assert stop(monkeypatch, task) == 2
    capsys.readouterr()


def test_strict_requires_the_feature_profile_or_a_stronger_one(
    task: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    configure(task, smoke=[PASSING], feature=[PASSING], full=[PASSING])
    prepare(task, "strict", capsys)
    quality(task, "smoke", capsys)
    assert stop(monkeypatch, task) == 2
    assert "no `feature` quality receipt" in capsys.readouterr().err
    quality(task, "full", capsys)
    assert stop(monkeypatch, task) == 0


def test_an_empty_profile_is_satisfied_by_its_skipped_receipt(
    task: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    prepare(task, "lean", capsys)
    quality(task, "smoke", capsys)
    assert stop(monkeypatch, task) == 0


def test_a_task_checkpointed_as_blocked_may_stop(
    task: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    prepare(task, "lean", capsys)
    main(["--root", str(task), "sync-tasks"])
    main(["--root", str(task), "checkpoint", "--status", "blocked", "--blocker", "waiting for the API"])
    capsys.readouterr()
    assert stop(monkeypatch, task) == 0


def test_repeated_stops_release_the_agent_and_block_the_run(
    task: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    prepare(task, "lean", capsys)
    assert [stop(monkeypatch, task) for _ in range(3)] == [2, 2, 2]
    capsys.readouterr()
    assert stop(monkeypatch, task) == 0
    warning = json.loads(capsys.readouterr().out)
    assert "quality-receipt-required" in warning["systemMessage"]
    run = current_run(task)
    assert run["status"] == "blocked"
    assert "smoke" in run["blocker"]
    log = (task / ".jotta" / "runtime" / "logs" / "hooks.jsonl").read_text(encoding="utf-8").splitlines()
    assert [json.loads(line)["decision"] for line in log] == ["block", "block", "block", "warn"]


def test_the_required_profile_is_configurable(
    task: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    gates = task / ".jotta" / "sensors" / "computational" / "gates.json"
    data = json.loads(gates.read_text(encoding="utf-8"))
    data["completion"] = {"profiles": {"lean": None}}
    gates.write_text(json.dumps(data), encoding="utf-8")
    prepare(task, "lean", capsys)
    assert stop(monkeypatch, task) == 0
