from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from jotta.adapters import permissions
from jotta.cli import main
from jotta.core.paths import ProjectPaths
from jotta.core.state import JSONDict


def set_profile(project: Path, profile: str) -> None:
    config = project / ".jotta" / "config.yaml"
    text = re.sub(r"execution_profile: \S+", f"execution_profile: {profile}", config.read_text(encoding="utf-8"))
    config.write_text(text, encoding="utf-8")


def adapt(project: Path, capsys: pytest.CaptureFixture[str], agent: str, *extra: str) -> JSONDict:
    assert main(["--root", str(project), "adapter", agent, *extra]) == 0
    data: JSONDict = json.loads(capsys.readouterr().out)
    return data


def claude_permissions(project: Path) -> JSONDict:
    data: JSONDict = json.loads((project / ".claude" / "settings.json").read_text(encoding="utf-8"))["permissions"]
    return data


def opencode_shell(project: Path) -> list[tuple[str, str]]:
    lines = (project / ".opencode" / "opencode.jsonc").read_text(encoding="utf-8").splitlines()
    data = json.loads("\n".join(line for line in lines if not line.startswith("//")))
    return [(rule["resource"], rule["effect"]) for rule in data["permissions"] if rule["action"] == "shell"]


def test_the_active_profile_comes_from_the_config(project: Path) -> None:
    paths = ProjectPaths(project)
    assert permissions.active_profile(paths) == "lean"
    set_profile(project, "strict")
    assert permissions.active_profile(paths) == "strict"


def test_profile_rules_add_common_rules_and_gate_commands(project: Path) -> None:
    gates = project / ".jotta" / "sensors" / "computational" / "gates.json"
    data = json.loads(gates.read_text(encoding="utf-8"))
    data["profiles"]["smoke"] = ["npm run lint", "git status *"]
    gates.write_text(json.dumps(data), encoding="utf-8")
    rules = permissions.shell_rules(ProjectPaths(project), "manual-classic")
    assert rules.allow[0] == "git status *"
    assert rules.allow.count("git status *") == 1
    assert "npm run lint" in rules.allow
    assert "git commit *" in rules.ask
    assert rules.deny == ["gh pr merge *"]


def test_an_unknown_profile_is_rejected(project: Path) -> None:
    with pytest.raises(ValueError, match="unknown execution profile 'yolo'"):
        permissions.shell_rules(ProjectPaths(project), "yolo")


def test_a_project_without_the_file_gets_no_profile_rules(project: Path) -> None:
    (project / ".jotta" / "policy" / "profile-permissions.json").unlink()
    rules = permissions.shell_rules(ProjectPaths(project))
    assert (rules.profile, rules.allow, rules.ask, rules.deny) == ("lean", [], [], [])


@pytest.mark.parametrize(
    ("pattern", "valid"),
    [("git status *", True), ("pwd", True), ("git * push", False), ("git status*", False), (" ls", False), (3, False)],
)
def test_patterns_allow_only_a_trailing_wildcard(pattern: object, valid: bool) -> None:
    assert permissions.valid_pattern(pattern) is valid


def test_validate_reports_every_problem() -> None:
    document = {
        "common": {"allow": ["rm *-rf"]},
        "profiles": {"lean": {"ask": "git push *"}, "strict": {}, "turbo": {}},
    }
    assert permissions.validate(document) == [
        "invalid pattern in `common.allow`: 'rm *-rf'",
        "`lean.ask` is not a list",
        "`manual-classic` is missing or not an object",
        "unknown profile `turbo`",
    ]
    assert permissions.validate([]) == ["the file is not a JSON object"]


def test_switching_the_profile_replaces_the_claude_rules(project: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (project / ".claude").mkdir()
    user = {"permissions": {"allow": ["Bash(make test)"], "deny": ["Read(./secrets/**)"]}}
    (project / ".claude" / "settings.json").write_text(json.dumps(user), encoding="utf-8")
    assert adapt(project, capsys, "claude")["profile"] == "lean"
    lean = claude_permissions(project)
    assert "Bash(git commit *)" in lean["allow"]
    assert "Bash(git push *)" in lean["ask"]
    set_profile(project, "manual-classic")
    adapt(project, capsys, "claude")
    manual = claude_permissions(project)
    assert manual["allow"][0] == "Bash(make test)"
    assert "Bash(git commit *)" not in manual["allow"]
    assert "Bash(git commit *)" in manual["ask"]
    assert manual["deny"] == ["Read(./secrets/**)", "Bash(gh pr merge *)"]
    record = json.loads((project / ".claude" / "jotta-permissions.json").read_text(encoding="utf-8"))
    assert record["profile"] == "manual-classic"


def test_the_profile_option_overrides_the_config(project: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert adapt(project, capsys, "codex", "--profile", "strict")["profile"] == "strict"
    rules = (project / ".codex" / "rules" / "jotta.rules").read_text(encoding="utf-8")
    assert "# profile: strict" in rules
    assert 'pattern = ["git", "commit"],\n    decision = "prompt",' in rules
    assert '"allow"' not in rules
    adapt(project, capsys, "codex", "--profile", "manual-classic")
    rules = (project / ".codex" / "rules" / "jotta.rules").read_text(encoding="utf-8")
    assert 'pattern = ["gh", "pr", "merge"],\n    decision = "forbidden",' in rules


def test_opencode_applies_the_profile_before_the_fixed_denials(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    adapt(project, capsys, "opencode")
    lean = opencode_shell(project)
    assert lean[0] == ("*", "ask")
    assert ("jotta *", "allow") in lean
    assert lean.index(("jotta *", "allow")) < lean.index(("jotta scope allow*", "deny"))
    set_profile(project, "manual-classic")
    adapt(project, capsys, "opencode")
    manual = opencode_shell(project)
    assert ("jotta *", "allow") not in manual
    assert ("gh pr merge *", "deny") in manual


def test_doctor_reports_a_stale_profile_and_an_invalid_file(project: Path, capsys: pytest.CaptureFixture[str]) -> None:
    adapt(project, capsys, "opencode")
    set_profile(project, "strict")
    main(["--root", str(project), "doctor"])
    assert "opencode configuration is out of date" in capsys.readouterr().out
    adapt(project, capsys, "opencode")
    main(["--root", str(project), "doctor"])
    assert "out of date" not in capsys.readouterr().out
    source = project / ".jotta" / "policy" / "profile-permissions.json"
    source.write_text('{"profiles": {}}', encoding="utf-8")
    assert main(["--root", str(project), "doctor"]) == 1
    assert "profile permissions: `common` is missing or not an object" in capsys.readouterr().out
    set_profile(project, "yolo")
    main(["--root", str(project), "doctor"])
    assert "unknown execution profile in config.yaml: yolo" in capsys.readouterr().out


def test_an_invalid_file_blocks_the_adapter(project: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (project / ".jotta" / "policy" / "profile-permissions.json").write_text("{}", encoding="utf-8")
    assert main(["--root", str(project), "adapter", "claude"]) == 2
    result = json.loads(capsys.readouterr().out)
    assert result["error"].startswith("cannot read the profile permissions")
    assert not (project / ".claude").exists()
