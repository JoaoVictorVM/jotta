from __future__ import annotations

import json
from pathlib import Path

import pytest

from jotta.adapters.claude import first_paragraph, merge_settings, missing_hooks, split_frontmatter
from jotta.cli import main
from jotta.core.paths import ProjectPaths
from jotta.core.state import JSONDict

HOOK_COMMANDS = {
    "PreToolUse": "jotta hook pre-tool-use",
    "PostToolUse": "jotta hook post-tool-use",
    "Stop": "jotta hook stop",
}


def adapt(project: Path, capsys: pytest.CaptureFixture[str], *extra: str) -> tuple[int, JSONDict]:
    code = main(["--root", str(project), "adapter", "claude", *extra])
    data: JSONDict = json.loads(capsys.readouterr().out)
    return code, data


def settings(project: Path) -> JSONDict:
    data: JSONDict = json.loads((project / ".claude" / "settings.json").read_text(encoding="utf-8"))
    return data


def commands(data: JSONDict, event: str) -> list[str]:
    return [hook["command"] for group in data["hooks"][event] for hook in group["hooks"]]


def test_the_adapter_wires_hooks_agents_and_skills(project: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code, result = adapt(project, capsys)
    assert (code, result["status"], result["skipped"]) == (0, "configured", [])
    data = settings(project)
    for event, command in HOOK_COMMANDS.items():
        assert commands(data, event) == [command]
    assert data["hooks"]["PreToolUse"][0]["matcher"].startswith("Bash|Read|")
    assert "matcher" not in data["hooks"]["Stop"][0]

    agents = {path.stem for path in (project / ".claude" / "agents").glob("*.md")}
    assert agents == {path.stem for path in (project / ".jotta" / "agents").glob("*.md")}
    skills = {path.parent.name for path in (project / ".claude" / "skills").glob("*/SKILL.md")}
    assert skills == {path.parent.name for path in (project / ".jotta" / "skills").glob("*/SKILL.md")}
    assert missing_hooks(ProjectPaths(project)) == []


@pytest.mark.parametrize(("agent", "tools"), [("reviewer", "Read, Grep, Glob"), ("qa-reviewer", "Read, Grep, Glob")])
def test_reviewers_only_get_read_only_tools(
    project: Path, capsys: pytest.CaptureFixture[str], agent: str, tools: str
) -> None:
    adapt(project, capsys)
    fields, body = split_frontmatter((project / ".claude" / "agents" / f"{agent}.md").read_text(encoding="utf-8"))
    assert fields["name"] == agent
    assert fields["tools"] == tools
    assert fields["description"]
    assert "Never modify code" in body or "Does not write code" in body


def test_writers_inherit_every_tool(project: Path, capsys: pytest.CaptureFixture[str]) -> None:
    adapt(project, capsys)
    fields, _ = split_frontmatter((project / ".claude" / "agents" / "implementer.md").read_text(encoding="utf-8"))
    assert "tools" not in fields
    assert fields["description"].startswith("Implement one prepared task")


def test_a_skill_entry_points_to_the_canonical_skill(project: Path, capsys: pytest.CaptureFixture[str]) -> None:
    adapt(project, capsys)
    entry = (project / ".claude" / "skills" / "spec-writer" / "SKILL.md").read_text(encoding="utf-8")
    canonical, _ = split_frontmatter(
        (project / ".jotta" / "skills" / "spec-writer" / "SKILL.md").read_text(encoding="utf-8")
    )
    fields, body = split_frontmatter(entry)
    assert fields == {"name": canonical["name"], "description": canonical["description"]}
    assert "Read `.jotta/skills/spec-writer/SKILL.md` completely" in body
    assert "`.jotta/skills/spec-writer/`" in body


def test_existing_settings_are_merged_without_losing_anything(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    permissions = {"allow": ["Bash(npm test)"]}
    session_start = [{"hooks": [{"type": "command", "command": "echo hi"}]}]
    audit = [{"matcher": "Bash", "hooks": [{"type": "command", "command": "./scripts/audit.sh"}]}]
    existing = {"permissions": permissions, "hooks": {"PreToolUse": audit, "SessionStart": session_start}}
    (project / ".claude").mkdir()
    (project / ".claude" / "settings.json").write_text(json.dumps(existing), encoding="utf-8")
    adapt(project, capsys)
    data = settings(project)
    assert data["permissions"] == permissions
    assert data["hooks"]["SessionStart"] == session_start
    assert commands(data, "PreToolUse") == ["./scripts/audit.sh", "jotta hook pre-tool-use"]


def test_running_twice_changes_nothing(project: Path, capsys: pytest.CaptureFixture[str]) -> None:
    adapt(project, capsys)
    before = settings(project)
    code, result = adapt(project, capsys)
    assert (code, result["written"]) == (0, [])
    assert result["unchanged"] > 0
    assert settings(project) == before


def test_user_files_are_never_overwritten(project: Path, capsys: pytest.CaptureFixture[str]) -> None:
    own = project / ".claude" / "agents" / "reviewer.md"
    own.parent.mkdir(parents=True)
    own.write_text("---\nname: reviewer\ndescription: mine\n---\n\nMy reviewer.\n", encoding="utf-8")
    code, result = adapt(project, capsys)
    assert code == 0
    assert result["skipped"] == [".claude/agents/reviewer.md"]
    assert own.read_text(encoding="utf-8").endswith("My reviewer.\n")


def test_generated_files_follow_the_source(project: Path, capsys: pytest.CaptureFixture[str]) -> None:
    adapt(project, capsys)
    source = project / ".jotta" / "agents" / "reviewer.md"
    source.write_text(source.read_text(encoding="utf-8") + "\nAlso check the changelog.\n", encoding="utf-8")
    _, result = adapt(project, capsys)
    assert result["written"] == [".claude/agents/reviewer.md"]
    assert "Also check the changelog." in (project / ".claude" / "agents" / "reviewer.md").read_text(encoding="utf-8")


@pytest.mark.parametrize("content", ["{not json", "[]", '{"hooks": []}', '{"hooks": {"Stop": {}}}'])
def test_invalid_settings_block_the_adapter(project: Path, capsys: pytest.CaptureFixture[str], content: str) -> None:
    (project / ".claude").mkdir()
    (project / ".claude" / "settings.json").write_text(content, encoding="utf-8")
    code, result = adapt(project, capsys)
    assert (code, result["status"]) == (2, "blocked")
    assert result["error"].startswith("cannot merge .claude/settings.json")
    assert not (project / ".claude" / "agents").exists()
    assert (project / ".claude" / "settings.json").read_text(encoding="utf-8") == content


def test_dry_run_writes_nothing(project: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code, result = adapt(project, capsys, "--dry-run")
    assert (code, result["status"]) == (0, "dry-run")
    assert ".claude/settings.json" in result["written"]
    assert not (project / ".claude").exists()


def test_doctor_warns_until_the_hooks_are_configured(project: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--root", str(project), "doctor"]) == 0
    assert "Claude Code hooks not configured (PreToolUse, PostToolUse, Stop)" in capsys.readouterr().out
    adapt(project, capsys)
    assert main(["--root", str(project), "doctor"]) == 0
    assert "Claude Code hooks" not in capsys.readouterr().out


def test_merge_keeps_an_existing_jotta_hook_once() -> None:
    once = merge_settings({})
    assert merge_settings(once) == once


def test_first_paragraph_skips_headings() -> None:
    assert (
        first_paragraph("# Agent: x\n\n## Role\n\nReview in a clean\ncontext.\n\nMore.") == "Review in a clean context."
    )
    assert first_paragraph("# Only a title\n") == ""
