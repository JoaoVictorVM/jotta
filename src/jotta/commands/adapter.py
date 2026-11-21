"""The ``jotta adapter`` command."""

from __future__ import annotations

import argparse
from collections.abc import Callable

from jotta.adapters import claude, codex, opencode, permissions
from jotta.adapters.common import AdapterPlan, apply_adapter
from jotta.core.paths import ProjectPaths
from jotta.core.state import JSONDict, print_json

EXIT_OK = 0
EXIT_BLOCKED = 2
PLANNERS: dict[str, Callable[[ProjectPaths, str | None], AdapterPlan]] = {
    "claude": claude.plan_adapter,
    "codex": codex.plan_adapter,
    "opencode": opencode.plan_adapter,
}
AGENT_DIRECTORIES = {"claude": ".claude", "codex": ".codex", "opencode": ".opencode"}


def configure(paths: ProjectPaths, agent: str, profile: str | None = None) -> JSONDict:
    """Write the configuration of ``agent`` unless an existing hook file cannot be merged."""
    plan = PLANNERS[agent](paths, profile)
    if plan.error is None:
        apply_adapter(plan)
    return plan.summary()


def outdated(paths: ProjectPaths) -> list[str]:
    """The agents whose generated configuration differs from what the harness and the active profile produce."""
    stale = []
    for agent, directory in AGENT_DIRECTORIES.items():
        if not (paths.root / directory).is_dir():
            continue
        plan = PLANNERS[agent](paths, None)
        if plan.error is None and plan.writes:
            stale.append(agent)
    return stale


def run(paths: ProjectPaths, args: argparse.Namespace) -> int:
    profile = args.profile or permissions.active_profile(paths)
    plan = PLANNERS[args.agent](paths, profile)
    summary = {"profile": profile, **plan.summary()}
    if plan.error:
        print_json({"status": "blocked", "message": "no files were written", **summary})
        return EXIT_BLOCKED
    if args.dry_run:
        print_json({"status": "dry-run", **summary})
        return EXIT_OK
    apply_adapter(plan)
    print_json({"status": "configured", **summary})
    return EXIT_OK
