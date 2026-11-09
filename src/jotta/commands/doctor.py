"""Check the integrity of an installed harness."""

from __future__ import annotations

import json
import re

from jotta.core.context import profile_token_estimates
from jotta.core.paths import ProjectPaths
from jotta.core.state import load_json
from jotta.isolation import orca
from jotta.routing import router

SKILL_REFERENCE = re.compile(r"\]\((references/[^)]+)\)")


def run(paths: ProjectPaths) -> int:
    errors: list[str] = []
    warnings: list[str] = []
    for path in paths.required():
        if not path.exists():
            errors.append(f"absent: {path.relative_to(paths.root)}")
    json_files = (
        paths.tasks,
        paths.run,
        paths.usage,
        paths.routing,
        paths.budget_policy,
        paths.budget_providers,
        paths.gates,
    )
    for path in json_files:
        if path.exists():
            try:
                load_json(path)
            except (OSError, json.JSONDecodeError) as exc:
                errors.append(f"invalid JSON {path.relative_to(paths.root)}: {exc}")
    for skill in paths.skills.glob("*/SKILL.md"):
        text = skill.read_text(encoding="utf-8")
        if not text.startswith("---\n") or "\nname:" not in text or "\ndescription:" not in text:
            errors.append(f"invalid skill frontmatter: {skill.relative_to(paths.root)}")
        for reference in SKILL_REFERENCE.findall(text):
            if not (skill.parent / reference).exists():
                errors.append(f"broken skill reference: {skill.parent.relative_to(paths.root)}/{reference}")
    try:
        errors.extend(f"model routing: {error}" for error in router.validate(router.load(paths.routing)))
    except (OSError, ValueError, KeyError) as exc:
        errors.append(f"model routing unavailable: {exc}")
    if not orca.available():
        warnings.append("Orca CLI unavailable in this shell; autonomous GitHub worktree launch will stop")
    print("DOCTOR FAILED" if errors else "DOCTOR OK")
    for error in errors:
        print(f"- {error}")
    for warning in warnings:
        print(f"- WARNING: {warning}")
    estimates = profile_token_estimates(paths.skills)
    print(f"- static skill estimate lean: {estimates.get('lean', 0)} tokens")
    print(f"- static skill estimate strict: {estimates.get('strict', 0)} tokens")
    return 1 if errors else 0
