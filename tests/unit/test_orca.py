from __future__ import annotations

import argparse
import json
import subprocess
from typing import Any

import pytest

from jotta.isolation import orca


class FakeOrca:
    """Records Orca invocations and answers each subcommand with canned JSON."""

    def __init__(self, responses: dict[str, Any] | None = None, returncode: int = 0, stdout: str | None = None):
        self.calls: list[list[str]] = []
        self.responses = responses or {}
        self.returncode = returncode
        self.stdout = stdout

    def __call__(self, command: list[str], **_: Any) -> subprocess.CompletedProcess[str]:
        self.calls.append(command)
        key = " ".join(command[1:3])
        stdout = self.stdout if self.stdout is not None else json.dumps(self.responses.get(key, {"ok": True}))
        return subprocess.CompletedProcess(command, self.returncode, stdout=stdout, stderr="boom")


@pytest.fixture(autouse=True)
def orca_on_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ORCA_CLI_COMMAND", raising=False)
    monkeypatch.delenv("ORCA_DEV_REPO_ROOT", raising=False)
    monkeypatch.setattr("jotta.isolation.orca.platform.system", lambda: "Windows")
    monkeypatch.setattr("jotta.isolation.orca.shutil.which", lambda name: f"/bin/{name}")


def install(monkeypatch: pytest.MonkeyPatch, fake: FakeOrca) -> FakeOrca:
    monkeypatch.setattr("jotta.isolation.orca.subprocess.run", fake)
    return fake


def test_prefix_follows_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    assert orca.command_prefix() == ["orca"]
    monkeypatch.setattr("jotta.isolation.orca.platform.system", lambda: "Linux")
    assert orca.command_prefix() == ["orca-ide"]
    monkeypatch.setenv("ORCA_DEV_REPO_ROOT", "/repo")
    assert orca.command_prefix() == ["orca-dev"]
    monkeypatch.setenv("ORCA_CLI_COMMAND", "node orca.js")
    assert orca.command_prefix() == ["node", "orca.js"]


def test_missing_cli_is_reported(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("jotta.isolation.orca.shutil.which", lambda name: None)
    assert not orca.available()
    with pytest.raises(orca.OrcaError, match="Orca CLI unavailable"):
        orca.command_prefix()


def test_invoke_appends_json_and_parses_the_output(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = install(monkeypatch, FakeOrca({"skills get": {"name": "orca-cli"}}))
    assert orca.load_guide() == {"name": "orca-cli"}
    assert fake.calls == [["orca", "skills", "get", "orca-cli", "--json"]]


def test_failed_command_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    install(monkeypatch, FakeOrca(returncode=1))
    with pytest.raises(orca.OrcaError, match="boom"):
        orca.invoke(["worktree", "list"])


def test_invalid_json_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    install(monkeypatch, FakeOrca(stdout="not json"))
    with pytest.raises(orca.OrcaError, match="Invalid Orca JSON"):
        orca.invoke(["worktree", "list"])


def test_create_worktree_loads_the_guide_and_normalizes_the_result(monkeypatch: pytest.MonkeyPatch) -> None:
    created = {
        "result": {
            "id": "wt-1",
            "path": "/work/wt-1",
            "branch": "feat/login",
            "launch": {"outcome": {"handle": "term-7", "kind": "terminal"}, "prompt": {"outcome": "sent"}},
        }
    }
    fake = install(monkeypatch, FakeOrca({"worktree create": created}))
    result = orca.create_worktree("login", "claude", "implement F01", model="model-x", effort="high")

    assert fake.calls[0][1:3] == ["skills", "get"]
    command = fake.calls[1]
    assert command[1:3] == ["worktree", "create"]
    assert "--no-parent" in command
    assert command[command.index("--model") + 1] == "model-x"
    assert command[command.index("--effort") + 1] == "high"
    assert {key: result[key] for key in ("worktree_id", "worktree_path", "branch", "worker_handle")} == {
        "worktree_id": "wt-1",
        "worktree_path": "/work/wt-1",
        "branch": "feat/login",
        "worker_handle": "term-7",
    }
    assert result["prompt_outcome"] == "sent"


def test_cleanup_closes_terminals_before_removing(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = install(monkeypatch, FakeOrca())
    orca.cleanup("wt-1")
    assert [call[1:3] for call in fake.calls] == [["skills", "get"], ["terminal", "close"], ["worktree", "rm"]]


def test_run_blocks_when_orca_fails(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    install(monkeypatch, FakeOrca(returncode=1))
    assert orca.run(argparse.Namespace(orca_command="guide")) == orca.EXIT_BLOCKED
    assert json.loads(capsys.readouterr().out)["status"] == "blocked"
