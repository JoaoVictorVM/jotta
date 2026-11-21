"""Shell permissions per execution profile, shared by the agent adapters.

``.jotta/policy/profile-permissions.json`` lists shell command patterns to allow, ask about or deny, common to every
profile and specific to ``lean``, ``strict`` and ``manual-classic``. The adapters translate the rules of the active
profile, read from ``defaults.execution_profile`` in ``config.yaml``, into each agent's own format. A pattern is a
command, or a command prefix followed by `` *``; every agent reads that form the same way.
"""

from __future__ import annotations

import json
import re
import shlex
from dataclasses import dataclass, field
from pathlib import Path

from jotta.core.paths import ProjectPaths
from jotta.core.state import JSONDict

PROFILES = ("lean", "strict", "manual-classic")
DEFAULT_PROFILE = "lean"
EFFECTS = ("allow", "ask", "deny")
EXECUTION_PROFILE = re.compile(r"^\s+execution_profile:\s*([A-Za-z0-9_-]+)\s*$", re.M)


@dataclass(frozen=True)
class ShellRules:
    """The shell rules of one profile, each list without duplicates and in file order."""

    profile: str
    allow: list[str] = field(default_factory=list)
    ask: list[str] = field(default_factory=list)
    deny: list[str] = field(default_factory=list)

    def by_effect(self) -> dict[str, list[str]]:
        return {"allow": self.allow, "ask": self.ask, "deny": self.deny}


def source(paths: ProjectPaths) -> Path:
    return paths.policy / "profile-permissions.json"


def active_profile(paths: ProjectPaths) -> str:
    """The profile named by ``defaults.execution_profile`` in ``config.yaml``, or ``lean``."""
    try:
        match = EXECUTION_PROFILE.search((paths.harness / "config.yaml").read_text(encoding="utf-8"))
    except OSError:
        return DEFAULT_PROFILE
    return match.group(1) if match else DEFAULT_PROFILE


def valid_pattern(pattern: object) -> bool:
    if not isinstance(pattern, str) or not pattern.strip() or pattern != pattern.strip():
        return False
    head = pattern[:-2] if pattern.endswith(" *") else pattern
    return bool(head) and "*" not in head


def validate(data: object) -> list[str]:
    """Every problem in a profile permissions document."""
    if not isinstance(data, dict):
        return ["the file is not a JSON object"]
    errors: list[str] = []
    sections: dict[str, object] = {"common": data.get("common")}
    profiles = data.get("profiles")
    if not isinstance(profiles, dict):
        return ["`profiles` is not an object"]
    sections.update({name: profiles.get(name) for name in PROFILES})
    for name, section in sections.items():
        if not isinstance(section, dict):
            errors.append(f"`{name}` is missing or not an object")
            continue
        for effect in EFFECTS:
            patterns = section.get(effect, [])
            if not isinstance(patterns, list):
                errors.append(f"`{name}.{effect}` is not a list")
                continue
            errors.extend(
                f"invalid pattern in `{name}.{effect}`: {item!r}" for item in patterns if not valid_pattern(item)
            )
    errors.extend(f"unknown profile `{name}`" for name in profiles if name not in PROFILES)
    return errors


def load(paths: ProjectPaths) -> JSONDict:
    data = json.loads(source(paths).read_text(encoding="utf-8"))
    errors = validate(data)
    if errors:
        raise ValueError(f"{paths.relative(source(paths))}: {errors[0]}")
    result: JSONDict = data
    return result


def gate_commands(paths: ProjectPaths) -> list[str]:
    """The quality profile commands, which every profile may run without asking."""
    try:
        profiles = json.loads(paths.gates.read_text(encoding="utf-8")).get("profiles", {})
    except (OSError, ValueError, AttributeError):
        return []
    if not isinstance(profiles, dict):
        return []
    commands = [command for value in profiles.values() if isinstance(value, list) for command in value]
    return [command for command in commands if isinstance(command, str) and valid_pattern(command)]


def unique(items: list[str]) -> list[str]:
    return list(dict.fromkeys(items))


def shell_rules(paths: ProjectPaths, profile: str | None = None) -> ShellRules:
    """The shell rules of ``profile``, or of the active profile when it is not given."""
    name = profile or active_profile(paths)
    if name not in PROFILES:
        raise ValueError(f"unknown execution profile {name!r}; expected one of {', '.join(PROFILES)}")
    if not source(paths).is_file():
        return ShellRules(profile=name)
    data = load(paths)
    common, own = data["common"], data["profiles"][name]
    rules = {effect: [*common.get(effect, []), *own.get(effect, [])] for effect in EFFECTS}
    return ShellRules(
        profile=name,
        allow=unique([*rules["allow"], *gate_commands(paths)]),
        ask=unique(rules["ask"]),
        deny=unique(rules["deny"]),
    )


def words(pattern: str) -> list[str]:
    """The argument prefix a pattern matches, for agents that match commands as argument lists."""
    head = pattern[:-2] if pattern.endswith(" *") else pattern
    try:
        return shlex.split(head)
    except ValueError:
        return head.split()
