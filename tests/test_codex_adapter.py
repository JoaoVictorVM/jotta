from __future__ import annotations

import io
import json
import subprocess
import sys
from pathlib import Path

import pytest

from jotta.cli import main
from jotta.core.state import JSONDict

PYTHON = f'"{sys.executable}"'
FAILING = f"{PYTHON} -c \"import sys; print('app.py:1:1: E999 broken'); sys.exit(1)\""
PRD = """# PRD

| ID | Feature | Priority | Dependencies |
|---|---|---|---|
| F03 | Tela inicial | 1 | none |
"""
SPEC = "| File Path | New/Modified |\n|---|---|\n| `src/home.py` | New |\n"


def patch(*lines: str) -> str:
    return "\n".join(["*** Begin Patch", *lines, "*** End Patch"])


def adapt(project: Path, capsys: pytest.CaptureFixture[str], *extra: str) -> tuple[int, JSONDict]:
    code = main(["--root", str(project), "adapter", "codex", *extra])
    data: JSONDict = json.loads(capsys.readouterr().out)
    return code, data


def hook(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], event: str, payload: JSONDict
) -> tuple[int, str]:
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
    code = main(["hook", event, "--agent", "codex"])
    return code, capsys.readouterr().out


def apply_patch(project: Path, text: str) -> JSONDict:
    return {
        "hook_event_name": "PreToolUse",
        "tool_name": "apply_patch",
        "tool_input": {"input": text},
        "cwd": str(project),
    }


def test_the_adapter_writes_hooks_config_agents_and_skills(project: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code, result = adapt(project, capsys)
    assert (code, result["status"], result["skipped"]) == (0, "configured", [])
    hooks = json.loads((project / ".codex" / "hooks.json").read_text(encoding="utf-8"))["hooks"]
    assert hooks["PreToolUse"] == [
        {
            "matcher": "Bash|apply_patch",
            "hooks": [{"type": "command", "command": "jotta hook pre-tool-use --agent codex"}],
        }
    ]
    assert hooks["PostToolUse"][0]["matcher"] == "apply_patch"
    assert hooks["Stop"] == [{"hooks": [{"type": "command", "command": "jotta hook stop --agent codex"}]}]
    config = (project / ".codex" / "config.toml").read_text(encoding="utf-8")
    assert 'approval_policy = "on-request"' in config
    assert 'sandbox_mode = "workspace-write"' in config
    agents = {path.stem for path in (project / ".codex" / "agents").glob("*.toml")}
    assert agents == {path.stem for path in (project / ".jotta" / "agents").glob("*.md")}
    skills = {path.parent.name for path in (project / ".agents" / "skills").glob("*/SKILL.md")}
    assert skills == {path.parent.name for path in (project / ".jotta" / "skills").glob("*/SKILL.md")}
    assert "Read `.jotta/skills/final-qa/SKILL.md`" in (
        project / ".agents" / "skills" / "final-qa" / "SKILL.md"
    ).read_text(encoding="utf-8")


def test_agent_files_are_valid_toml_and_reviewers_are_read_only(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    tomllib = pytest.importorskip("tomllib")
    adapt(project, capsys)
    reviewer = tomllib.loads((project / ".codex" / "agents" / "reviewer.toml").read_text(encoding="utf-8"))
    assert set(reviewer) == {"name", "description", "developer_instructions"}
    assert reviewer["name"] == "reviewer"
    assert reviewer["developer_instructions"].startswith("You are read-only.")
    assert "# Agent: reviewer" in reviewer["developer_instructions"]
    implementer = tomllib.loads((project / ".codex" / "agents" / "implementer.toml").read_text(encoding="utf-8"))
    assert implementer["developer_instructions"].startswith("# Agent: implementer")
    config = tomllib.loads((project / ".codex" / "config.toml").read_text(encoding="utf-8"))
    assert config["sandbox_workspace_write"] == {"network_access": False}


def test_existing_hooks_and_a_user_config_are_kept(project: Path, capsys: pytest.CaptureFixture[str]) -> None:
    codex = project / ".codex"
    codex.mkdir()
    audit = [{"matcher": "Bash", "hooks": [{"type": "command", "command": "./audit.sh"}]}]
    (codex / "hooks.json").write_text(json.dumps({"hooks": {"PreToolUse": audit}}), encoding="utf-8")
    (codex / "config.toml").write_text('model = "my-model"\n', encoding="utf-8")
    code, result = adapt(project, capsys)
    assert code == 0
    assert result["skipped"] == [".codex/config.toml"]
    hooks = json.loads((codex / "hooks.json").read_text(encoding="utf-8"))["hooks"]
    assert [group["hooks"][0]["command"] for group in hooks["PreToolUse"]] == [
        "./audit.sh",
        "jotta hook pre-tool-use --agent codex",
    ]
    assert (codex / "config.toml").read_text(encoding="utf-8") == 'model = "my-model"\n'
    _, again = adapt(project, capsys)
    assert again["written"] == []


def test_invalid_hooks_block_the_adapter(project: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (project / ".codex").mkdir()
    (project / ".codex" / "hooks.json").write_text("{oops", encoding="utf-8")
    code, result = adapt(project, capsys)
    assert (code, result["status"]) == (2, "blocked")
    assert result["error"].startswith("cannot merge .codex/hooks.json")
    assert not (project / ".agents").exists()


def test_doctor_checks_codex_hooks_only_in_a_codex_project(project: Path, capsys: pytest.CaptureFixture[str]) -> None:
    main(["--root", str(project), "doctor"])
    assert "Codex hooks" not in capsys.readouterr().out
    (project / ".codex").mkdir()
    main(["--root", str(project), "doctor"])
    assert "Codex hooks not configured (PreToolUse, PostToolUse, Stop)" in capsys.readouterr().out
    adapt(project, capsys)
    main(["--root", str(project), "doctor"])
    assert "Codex hooks" not in capsys.readouterr().out


def test_install_configures_codex(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    project = tmp_path / "project"
    subprocess.run(["git", "init", "-q", str(project)], check=True)
    assert main(["install", "--target", str(project)]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["codex"]["error"] is None
    assert (project / ".codex" / "hooks.json").is_file()
    exclude = (project / ".git" / "info" / "exclude").read_text(encoding="utf-8").splitlines()
    assert {"/.codex/", "/.agents/"} <= set(exclude)


def test_a_blocked_shell_command_is_denied_in_codex_format(
    project: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    payload = {"tool_name": "Bash", "tool_input": {"command": ["bash", "-lc", "git push --force"]}, "cwd": str(project)}
    code, out = hook(monkeypatch, capsys, "pre-tool-use", payload)
    assert code == 0
    decision = json.loads(out)["hookSpecificOutput"]
    assert (decision["hookEventName"], decision["permissionDecision"]) == ("PreToolUse", "deny")
    assert decision["permissionDecisionReason"].startswith("Blocked by the Jotta policy (force-push)")


def test_a_patch_touching_a_secret_is_denied(
    project: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    text = patch("*** Update File: src/app.py", "@@", "+x", "*** Update File: .env", "@@", "+TOKEN=1")
    code, out = hook(monkeypatch, capsys, "pre-tool-use", apply_patch(project, text))
    assert code == 0
    assert "(read-secrets)" in json.loads(out)["hookSpecificOutput"]["permissionDecisionReason"]


def test_a_patch_outside_the_strict_scope_is_denied(
    project: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    (project / ".planning" / "PRD.md").write_text(PRD, encoding="utf-8")
    folder = project / ".planning" / "features" / "F03-tela-inicial"
    folder.mkdir(parents=True)
    (folder / "spec.md").write_text(SPEC, encoding="utf-8")
    main(["--root", str(project), "prepare", "F03", "--profile", "strict"])
    capsys.readouterr()
    inside = patch("*** Update File: src/home.py", "@@", "+x")
    assert hook(monkeypatch, capsys, "pre-tool-use", apply_patch(project, inside)) == (0, "")
    outside = patch("*** Update File: src/home.py", "@@", "+x", "*** Add File: src/payments.py", "+y")
    code, out = hook(monkeypatch, capsys, "pre-tool-use", apply_patch(project, outside))
    assert "(edit-outside-task-scope)" in json.loads(out)["hookSpecificOutput"]["permissionDecisionReason"]


def test_a_failing_post_edit_check_is_fed_back_as_a_block(
    project: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    gates = project / ".jotta" / "sensors" / "computational" / "gates.json"
    data = json.loads(gates.read_text(encoding="utf-8"))
    data["profiles"]["smoke"] = [FAILING]
    gates.write_text(json.dumps(data), encoding="utf-8")
    docs_only = patch("*** Update File: README.md", "@@", "+x")
    assert hook(monkeypatch, capsys, "post-tool-use", apply_patch(project, docs_only)) == (0, "")
    code, out = hook(
        monkeypatch, capsys, "post-tool-use", apply_patch(project, patch("*** Add File: src/app.py", "+x"))
    )
    answer = json.loads(out)
    assert (code, answer["decision"]) == (0, "block")
    assert "E999 broken" in answer["reason"]


def test_stop_answers_with_json(
    project: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    payload = {"hook_event_name": "Stop", "stop_hook_active": False, "cwd": str(project)}
    assert hook(monkeypatch, capsys, "stop", payload) == (0, "{}\n")
    (project / ".planning" / "PRD.md").write_text(PRD, encoding="utf-8")
    main(["--root", str(project), "prepare", "F03"])
    capsys.readouterr()
    code, out = hook(monkeypatch, capsys, "stop", payload)
    answer = json.loads(out)
    assert (code, answer["decision"]) == (0, "block")
    assert "jotta quality smoke" in answer["reason"]
